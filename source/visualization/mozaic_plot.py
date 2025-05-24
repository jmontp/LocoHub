"""
User Guide:
This script visualizes phase-indexed biomechanical datasets in standardized Parquet format,
supporting both "split" (normalized) and "monolithic" formats.

Usage:
  # Launch interactive file dialog if no arguments given:
  python mozaic_plot.py

  # Monolithic format:
  python mozaic_plot.py --input_parquet path/to/data_monolithic.parquet \
      [--phase_col phase_r] [--subject_col subject_id] \
      [--task_col task_name] [--features hip_flexion_angle_rad knee_flexion_angle_rad]

  # Split format (requires metadata files):
  python mozaic_plot.py --input_parquet path/to/data_time.parquet \
      --metadata_subject metadata_subject.parquet \
      --metadata_task metadata_task.parquet \
      [--phase_col phase_r] [--subject_col subject_id] \
      [--task_col task_name] [--features hip_flexion_angle_rad knee_flexion_angle_rad]

Options:
  --input_parquet       Path to the main Parquet file (monolithic or fact table).
  --metadata_subject    Path to metadata_subject.parquet (for split format only).
  --metadata_task       Path to metadata_task.parquet (for split format only).
  --phase_col           Phase column name (default: phase_r).
  --subject_col         Subject ID column name (default: subject_id).
  --task_col            Task name column (default: task_name).
  --features            List of feature columns to include (default: auto-detect numeric fields).
  --output_html         Path to save HTML output (default: plots/[task_name].html).

Behavior:
  - If both metadata_subject and metadata_task are provided, the script merges them into the main dataframe before plotting.
  - If neither metadata file is provided, the script attempts to detect monolithic vs split:
      * Monolithic: proceeds if subject-level metadata columns (e.g., age, gender) are found in the main file.
      * Split: pops dialogs to select metadata_subject and metadata_task files.
  - Throws an error if the specified phase column is missing or metadata files are incompatible.
  - Generates one plot per unique task.
  - Creates a grid layout with features as columns and subjects as rows.
  - Saves all plots to HTML files in the plots directory by default.

Requirements:
  - pandas
  - plotly
  - tkinter (for file dialog, optional)
  - tqdm (for progress tracking)
"""
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.offline import plot as plotly_plot
from plotly.subplots import make_subplots
import os
import sys
import numpy as np
try:
    from tqdm import tqdm
except ImportError:
    # Simple tqdm fallback if not installed
    def tqdm(iterable, **kwargs):
        # print(f"Processing {len(iterable)} items...") # Removed for cleaner output
        return iterable

# Constants from standard specification
POINTS_PER_CYCLE = 150  # As defined in phase_calculation.md

def reshape_data_for_subject_task(subj_df: pd.DataFrame, features: list, phase_col: str) -> tuple[dict, np.ndarray | None]:
    """Reshapes data for a single subject within a single task into steps.

    Args:
        subj_df: DataFrame filtered for one subject and one task.
        features: List of feature column names to process.
        phase_col: Name of the phase column (e.g., 'phase_r').

    Returns:
        A tuple: (reshaped_feature_data, phase_x_axis)
        reshaped_feature_data: Dict where keys are feature names and values are
                               np.ndarrays of shape (num_steps, POINTS_PER_CYCLE).
        phase_x_axis: A 1D np.ndarray of shape (POINTS_PER_CYCLE,) for the x-axis,
                      or None if no valid data.
    """
    reshaped_feature_data = {}
    phase_x_axis = np.linspace(0, 100, POINTS_PER_CYCLE)

    # Check if subj_df is empty before proceeding
    if subj_df.empty:
        # print(f"[WARN] Empty DataFrame for subject-task, skipping reshaping.") # Debug
        return {}, None

    # Check if the phase column exists (should have been checked earlier too)
    if phase_col not in subj_df.columns:
        print(f"[ERROR] Phase column '{phase_col}' not found in subject-task DataFrame.")
        return {}, None

    # Use the first feature to determine the total number of data points for this subject-task
    # This assumes all feature columns have the same length for this subject-task combination,
    # which should be true for phase-indexed data where each cycle is 150 points.
    if not features:
        # print(f"[WARN] No features provided for reshaping.") # Debug
        return {}, None
    
    first_feature_data = subj_df[features[0]].values
    if len(first_feature_data) == 0:
        # print(f"[WARN] No data for first feature '{features[0]}' in subject-task, cannot determine steps.") # Debug
        return {}, None

    if len(first_feature_data) % POINTS_PER_CYCLE != 0:
        # Get subject and task info from the dataframe
        subject_id = subj_df['subject_id'].iloc[0] if 'subject_id' in subj_df.columns else 'unknown'
        task_name = subj_df['task_name'].iloc[0] if 'task_name' in subj_df.columns else 'unknown'
        
        print(f"[ERROR] Data length {len(first_feature_data)} for subject-task is not divisible by {POINTS_PER_CYCLE}.")
        print(f"        This violates the standard specification where each gait cycle must have exactly {POINTS_PER_CYCLE} points.")
        print(f"        Subject: {subject_id}, Task: {task_name}")
        print(f"        Expected multiples of {POINTS_PER_CYCLE}, got {len(first_feature_data)} points ({len(first_feature_data) / POINTS_PER_CYCLE:.2f} cycles)")
        print(f"        Please check the phase calculation in your data conversion pipeline.")
        return {}, None
    
    num_steps_expected = len(first_feature_data) // POINTS_PER_CYCLE

    for feat in features:
        if feat not in subj_df.columns:
            print(f"[WARN] Feature '{feat}' not found in subject-task DataFrame, skipping.")
            continue
        
        feat_array = subj_df[feat].values
        if len(feat_array) != len(first_feature_data):
            print(f"[ERROR] Feature '{feat}' has {len(feat_array)} points, but expected {len(first_feature_data)} based on first feature. Skipping feature.")
            continue

        try:
            # Reshape data: (total_points) -> (num_steps, POINTS_PER_CYCLE)
            reshaped_data = feat_array.reshape(num_steps_expected, POINTS_PER_CYCLE)
            reshaped_feature_data[feat] = reshaped_data
        except ValueError as e:
            print(f"[ERROR] Could not reshape data for feature '{feat}': {str(e)}. Total points: {len(feat_array)}, Expected steps: {num_steps_expected}")
            continue # Skip this feature
    
    if not reshaped_feature_data:
        # print(f"[WARN] No features were successfully reshaped for this subject-task.") # Debug
        return {}, None

    return reshaped_feature_data, phase_x_axis

def visualize_tasks(df: pd.DataFrame,
                    phase_col: str = 'phase_r',
                    subject_col: str = 'subject_id',
                    task_col: str = 'task_name',
                    features: list = None,
                    plots_dir: str = "plots",
                    diagnostic_mode: bool = False,
                    export_png: bool = False):
    """
    Generate one interactive plot per task with a grid layout.
    Features are organized as columns, subjects as rows.
    Data for each subject-task is reshaped into (num_steps, POINTS_PER_CYCLE) for each feature.
    Includes toggles for Mean+STD view and Individual Steps view.
    Saves each plot immediately after generation.
    """
    if phase_col not in df.columns:
        raise ValueError(f"Required phase column '{phase_col}' not found in dataframe")

    if features is None:
        # Auto-detect numeric features, excluding known non-feature columns
        exclude = {phase_col, subject_col, task_col, 'time_s', 'phase_l', 'phase_r'} # Added more specific exclusions
        candidates = [c for c in df.columns if c not in exclude and pd.api.types.is_numeric_dtype(df[c])]
        # Further filter: ensure feature has variability across subjects for the same task, or within a subject for a task
        features = []
        for c in candidates:
            if df.groupby([task_col, subject_col])[c].nunique().max() > 1 or \
               df.groupby(task_col)[c].nunique().max() > 1:
                features.append(c)
    
    if not features:
        print("[ERROR] No suitable features found for visualization. Please check data or specify features manually.")
        return {}

    print(f"Selected {len(features)} features for visualization: {', '.join(features)}")
    if len(features) > 20:
        print(f"Warning: Using only the first {min(len(features), 20)} features for better visualization clarity")
        features = features[:min(len(features), 20)]

    if not os.path.exists(plots_dir):
        os.makedirs(plots_dir)
        print(f"Created plots directory at: {plots_dir}")

    figs = {}
    unique_tasks = df[task_col].unique()
    
    # Diagnostic mode: check data format compliance
    if diagnostic_mode:
        print("\n=== DIAGNOSTIC MODE: Checking data format compliance ===")
        print(f"Standard specification: Each gait cycle must have exactly {POINTS_PER_CYCLE} points")
        print(f"Phase column: {phase_col}")
        print("\nChecking each subject-task combination:")
        
        issues_found = False
        for task in unique_tasks:
            task_df = df[df[task_col] == task]
            for subject in task_df[subject_col].unique():
                subj_task_df = task_df[task_df[subject_col] == subject]
                data_length = len(subj_task_df)
                
                if data_length % POINTS_PER_CYCLE != 0:
                    print(f"  ❌ {subject} - {task}: {data_length} points ({data_length/POINTS_PER_CYCLE:.2f} cycles)")
                    issues_found = True
                else:
                    num_cycles = data_length // POINTS_PER_CYCLE
                    print(f"  ✓ {subject} - {task}: {data_length} points ({num_cycles} complete cycles)")
        
        if issues_found:
            print("\n⚠️  Data format issues detected! The data does not comply with the standard.")
            print("   Each subject-task combination must have data length = n × 150 points")
            response = input("\nContinue with visualization anyway? (y/n): ")
            if response.lower() != 'y':
                print("Exiting...")
                return {}
        else:
            print("\n✅ All data complies with the standard format!")
        print("\n" + "="*60 + "\n")
    
    for task in tqdm(unique_tasks, desc="Generating and saving task plots"):
        task_df = df[df[task_col] == task]
        subjects = sorted(task_df[subject_col].unique()) # Sort subjects for consistent row order
        
        if not subjects:
            print(f"[WARN] No subjects found for task '{task}', skipping plot generation.")
            continue
        
        fig = make_subplots(
            rows=len(subjects), 
            cols=len(features),
            shared_xaxes=True,
            shared_yaxes='columns',
            subplot_titles=[f"{feat}" for feat in features],
            vertical_spacing=0.03,
            horizontal_spacing=0.03,
            row_titles=[f"Subj {str(subj)[:10]}" for subj in subjects]
        )
        
        colors = px.colors.qualitative.Plotly
        dash_styles = ['solid', 'dash', 'dot', 'dashdot']

        for i, subj in enumerate(subjects, 1):
            subj_task_df = task_df[task_df[subject_col] == subj].sort_values(by=phase_col)
            
            # Reshape data for this subject and task combination
            reshaped_subj_data, phase_x = reshape_data_for_subject_task(subj_task_df, features, phase_col)

            if not reshaped_subj_data or phase_x is None:
                print(f"[WARN] No valid data or failed to reshape for Subject {subj}, Task '{task}'. Skipping this subject in plot.")
                # Add empty placeholder traces or annotations if needed, or just skip
                for j, feat_name in enumerate(features, 1):
                     fig.add_trace(go.Scatter(x=[], y=[], mode='markers', name=f'NoData-{subj}-{feat_name}', showlegend=False), row=i, col=j)
                continue

            for j, feat_name in enumerate(features, 1):
                if feat_name not in reshaped_subj_data:
                    # print(f"[DEBUG] Feature '{feat_name}' not in reshaped data for Subj {subj}, Task {task}. Adding empty trace.") # Debug
                    fig.add_trace(go.Scatter(x=[], y=[], mode='markers', name=f'NoData-{subj}-{feat_name}', showlegend=False), row=i, col=j)
                    continue
                    
                steps_data = reshaped_subj_data[feat_name]  # Shape: (num_steps, 150)
                num_steps = steps_data.shape[0]
                
                if num_steps == 0:
                    # print(f"[DEBUG] Zero steps for Subj {subj}, Feature {feat_name}, Task {task}. Adding empty trace.") # Debug
                    fig.add_trace(go.Scatter(x=[], y=[], mode='markers', name=f'NoData-{subj}-{feat_name}', showlegend=False), row=i, col=j)
                    continue

                # Plot individual steps
                for step_k in range(num_steps):
                    fig.add_trace(go.Scatter(
                        x=phase_x,
                        y=steps_data[step_k],
                        mode='lines',
                        name=f'Subj{subj}-Feat{feat_name}-Step{step_k}',
                        line=dict(
                            width=1.5,
                            color=colors[step_k % len(colors)],
                            dash=dash_styles[step_k % len(dash_styles)]
                        ),
                        showlegend=False,
                        visible=False  # Hidden by default
                    ), row=i, col=j)
                
                # Calculate and plot mean/std
                mean_curve = np.mean(steps_data, axis=0)
                std_curve = np.std(steps_data, axis=0)
                
                fig.add_trace(go.Scatter(
                    x=phase_x, y=mean_curve,
                    mode='lines', name=f'Subj{subj}-Feat{feat_name}-Mean',
                    line=dict(width=2, color='rgba(0,0,0,0.8)'),
                    showlegend=False, visible=True
                ), row=i, col=j)
                fig.add_trace(go.Scatter(
                    x=phase_x, y=mean_curve + std_curve,
                    mode='lines', name=f'Subj{subj}-Feat{feat_name}-Upper',
                    line=dict(width=0), showlegend=False, visible=True
                ), row=i, col=j)
                fig.add_trace(go.Scatter(
                    x=phase_x, y=mean_curve - std_curve,
                    mode='lines', name=f'Subj{subj}-Feat{feat_name}-Lower',
                    line=dict(width=0), fill='tonexty',
                    fillcolor='rgba(0,0,0,0.15)',
                    showlegend=False, visible=True
                ), row=i, col=j)
        
        # Create visibility masks
        mean_std_visibility_mask = []
        individual_steps_visibility_mask = []
        for fig_trace in fig.data:
            trace_name = fig_trace.name if hasattr(fig_trace, 'name') else ''
            if 'Step' in trace_name:
                individual_steps_visibility_mask.append(True)
                mean_std_visibility_mask.append(False)
            elif 'Mean' in trace_name or 'Upper' in trace_name or 'Lower' in trace_name:
                individual_steps_visibility_mask.append(False)
                mean_std_visibility_mask.append(True)
            elif 'NoData' in trace_name: # Make sure NoData traces are handled correctly
                individual_steps_visibility_mask.append(False) # Or True if you want them to appear in a view
                mean_std_visibility_mask.append(False)     # Or True
            else:
                individual_steps_visibility_mask.append(False)
                mean_std_visibility_mask.append(False)
        
        fig.update_layout(
            title_text=f"<b>{task}</b> - Mean + STD View", # Bold task name
            height=max(400, 150 * len(subjects) + 50), # Add a bit more height for title/buttons
            width=max(800, 200 * len(features)),
            showlegend=False,
            template="plotly_white",
            updatemenus=[dict(
                type="buttons",
                direction="right",
                active=0,
                buttons=[
                    dict(label="Mean + STD",
                         method="update",
                         args=[{"visible": mean_std_visibility_mask},
                               {"title.text": f"<b>{task}</b> - Mean + STD View"}]),
                    dict(label="Individual Steps",
                         method="update",
                         args=[{"visible": individual_steps_visibility_mask},
                               {"title.text": f"<b>{task}</b> - Individual Steps View"}])
                ],
                pad={"r": 10, "t": 20}, # Increased top padding
                showactive=True,
                x=0.5, xanchor="center",
                y=1.02, # Adjusted y to give more space from title
                yanchor="bottom"
            )],
            margin=dict(t=80, b=50, l=50, r=50) # Adjust margins for better layout
        )
        
        for r_idx in range(1, len(subjects) + 1):
            for c_idx in range(1, len(features) + 1):
                fig.update_xaxes(title_text=f'{phase_col} (%)' if r_idx == len(subjects) else '', 
                                 row=r_idx, col=c_idx, range=[0, 100])
                fig.update_yaxes(autorange=True, row=r_idx, col=c_idx)
        
        figs[task] = fig
        
        # Save plot for the current task immediately
        safe_task_name = "".join(c if c.isalnum() else "_" for c in task)
        output_path = os.path.join(plots_dir, f"{safe_task_name}.html")
        try:
            html_content = fig.to_html(include_plotlyjs='cdn', full_html=True)
            # Add a header with task name (already done by title_text in layout)
            # html_content = html_content.replace('<body>', f'<body><h1>{task}</h1>') 
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            # print(f"Plot for '{task}' saved to: {output_path}") # Removed for cleaner tqdm output
        except Exception as e:
            print(f"[ERROR] Could not save plot for task '{task}' to {output_path}: {str(e)}")
        
        # Export PNG versions if requested
        if export_png:
            try:
                # Create PNG subdirectory if it doesn't exist
                png_dir = os.path.join(plots_dir, "png")
                if not os.path.exists(png_dir):
                    os.makedirs(png_dir)
                
                # Export Mean+STD view
                fig.update_layout(title_text=f"<b>{task}</b> - Mean + STD View")
                fig.update_traces(visible=mean_std_visibility_mask)
                png_path_mean = os.path.join(png_dir, f"{safe_task_name}_mean_std.png")
                fig.write_image(png_path_mean, width=max(800, 200 * len(features)), 
                               height=max(400, 150 * len(subjects) + 50))
                
                # Export Individual Steps view
                fig.update_layout(title_text=f"<b>{task}</b> - Individual Steps View")
                fig.update_traces(visible=individual_steps_visibility_mask)
                png_path_steps = os.path.join(png_dir, f"{safe_task_name}_individual_steps.png")
                fig.write_image(png_path_steps, width=max(800, 200 * len(features)), 
                               height=max(400, 150 * len(subjects) + 50))
                
                # Reset to default view
                fig.update_layout(title_text=f"<b>{task}</b> - Mean + STD View")
                fig.update_traces(visible=mean_std_visibility_mask)
                
                print(f"  📸 Exported PNGs: {safe_task_name}_mean_std.png, {safe_task_name}_individual_steps.png")
            except Exception as e:
                print(f"  ⚠️  Could not export PNG for task '{task}': {str(e)}")
                print(f"      Note: PNG export requires kaleido package. Install with: pip install kaleido")

    return figs

if __name__ == '__main__':
    import argparse
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        tk = None; filedialog = None

    parser = argparse.ArgumentParser(
        description='Visualize standardized locomotion phase-indexed dataframe.'
    )
    parser.add_argument('--input_parquet', nargs='?', help='Path to main Parquet file')
    parser.add_argument('--metadata_subject', help='Path to metadata_subject.parquet')
    parser.add_argument('--metadata_task', help='Path to metadata_task.parquet')
    parser.add_argument('--phase_col', default='phase_r', help='Name of the phase column (e.g., phase_r or phase_l)')
    parser.add_argument('--subject_col', default='subject_id')
    parser.add_argument('--task_col', default='task_name')
    parser.add_argument('--features', nargs='+', help='List of feature columns to plot. Auto-detects if not specified.')
    parser.add_argument('--diagnostic', action='store_true', help='Run diagnostic mode to check data format compliance')
    parser.add_argument('--export-png', dest='export_png', action='store_true', help='Export PNG versions of plots (requires kaleido)')
    # Removed --output_html as we save plots individually by task name
    # parser.add_argument('--output_html', help='Path to save HTML output (default: plots/[task_name].html)')
    args = parser.parse_args()

    input_file = args.input_parquet
    if not input_file:
        if tk and filedialog:
            root = tk.Tk(); root.withdraw()
            files = filedialog.askopenfilenames(
                title='Select main Parquet file',
                filetypes=[('Parquet files', '*.parquet'), ('All files', '*.*')]
            )
            if not files:
                parser.error('No file selected')
            input_file = files[0]
        else:
            parser.error('No input_parquet and tkinter not available')

    if not os.path.exists(input_file):
        parser.error(f'Input file "{input_file}" does not exist')

    print(f"Loading {input_file}...")
    try:
        df = pd.read_parquet(input_file)
        print(f"Loaded dataframe with shape {df.shape} and columns: {', '.join(df.columns)}")
    except Exception as e:
        print(f"Error loading parquet file: {e}")
        sys.exit(1)

    if not args.metadata_subject and not args.metadata_task:
        is_monolithic = "monolith" in input_file.lower()
        if not is_monolithic:
            if tk and filedialog:
                files = filedialog.askopenfilenames(
                    title='Select metadata_subject.parquet', filetypes=[('Parquet', '*.parquet')]
                )
                if not files:
                    parser.error('No metadata_subject file selected for split format')
                args.metadata_subject = files[0]
                files = filedialog.askopenfilenames(
                    title='Select metadata_task.parquet', filetypes=[('Parquet', '*.parquet')]
                )
                if not files:
                    parser.error('No metadata_task file selected for split format')
                args.metadata_task = files[0]
            else:
                parser.error('Non-monolithic file requires metadata files, but tkinter is unavailable for selection')

    if args.metadata_subject and args.metadata_task:
        if not os.path.exists(args.metadata_subject):
            parser.error(f'Metadata subject file "{args.metadata_subject}" does not exist')
        if not os.path.exists(args.metadata_task):
            parser.error(f'Metadata task file "{args.metadata_task}" does not exist')
        
        print(f"Loading metadata files...")
        try:
            meta_subj = pd.read_parquet(args.metadata_subject)
            meta_task_df = pd.read_parquet(args.metadata_task) # Renamed to avoid conflict
            print(f"Loaded metadata_subject with {len(meta_subj)} rows and metadata_task with {len(meta_task_df)} rows")
        except Exception as e:
            print(f"Error loading metadata files: {e}")
            sys.exit(1)
            
        # Basic validation of metadata files
        if args.subject_col not in meta_subj.columns:
            parser.error(f'Subject ID column "{args.subject_col}" not found in metadata_subject.parquet')
        if args.subject_col not in meta_task_df.columns or args.task_col not in meta_task_df.columns:
            parser.error(f'Required columns ("{args.subject_col}", "{args.task_col}") not found in metadata_task.parquet')
        
        print("Merging metadata with main dataframe...")
        df = df.merge(meta_subj, on=args.subject_col, how='left')
        # Ensure no duplicate columns from task metadata apart from join keys
        cols_to_use = [col for col in meta_task_df.columns if col not in df.columns or col in [args.subject_col, args.task_col]]
        df = df.merge(meta_task_df[cols_to_use], on=[args.subject_col, args.task_col], how='left')
        print(f"Merged dataframe shape: {df.shape}")
    elif args.metadata_subject or args.metadata_task: # Only one provided
        parser.error("Both metadata_subject and metadata_task must be provided for split format, or neither for monolithic.")

    # Determine script directory for plots output
    script_dir = os.path.dirname(os.path.abspath(__file__))
    plots_output_dir = os.path.join(script_dir, "plots")

    print("Generating and saving visualizations...")
    figs_dict = visualize_tasks(
        df,
        phase_col=args.phase_col,
        subject_col=args.subject_col,
        task_col=args.task_col,
        features=args.features,
        plots_dir=plots_output_dir,
        diagnostic_mode=args.diagnostic,
        export_png=args.export_png
    )
    
    if figs_dict:
        print(f"Successfully generated and saved {len(figs_dict)} task plots to '{plots_output_dir}'")
    else:
        print("No plots were generated.")

    print("Done!")
