"""
User Guide:
This script visualizes phase-indexed biomechanical datasets in standardized Parquet format.

Usage:
  # Launch interactive file dialog if no arguments given:
  python mozaic_plot.py

  # Specify input file and options:
  python mozaic_plot.py --input_parquet path/to/data.parquet \
      [--phase_col phase_%] [--subject_col subject_id] \
      [--task_col task_name] [--features hip_flexion_angle_rad knee_flexion_angle_rad] \
      [--output_html output.html]

Options:
  --input_parquet  Path to the Parquet file. If omitted, a file dialog will open.
  --phase_col      Phase column name (default: phase_%).
  --subject_col    Subject ID column name (default: subject_id).
  --task_col       Task name column (default: task_name).
  --features       List of feature columns to include (default: auto-detect numeric fields).
  --output_html    If set, all figures will be saved to this HTML file instead of displaying.

Behavior:
  - Throws an error if the specified phase column is missing.
  - Generates one plot per unique task.
  - Provides toggle buttons to switch between Mean+STD and Spaghetti views.

Requirements:
  - pandas
  - plotly
  - tkinter (for file dialog, optional)
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.offline import plot as plotly_plot


def visualize_tasks(df: pd.DataFrame,
                    phase_col: str = 'phase_%',
                    subject_col: str = 'subject_id',
                    task_col: str = 'task_name',
                    features: list = None):
    """
    Generate one interactive plot per task showing either mean+std or spaghetti plot per feature,
    specifically using phase as the x-axis.

    Parameters:
    - df: standardized dataframe containing phase index, subject_id, task_name, and feature columns
    - phase_col: name of the phase column (must exist in df)
    - subject_col: name of the subject identifier column
    - task_col: name of the task identifier column
    - features: list of feature columns to plot; if None, auto-detect based on schema

    Returns:
    - dict mapping task names to Plotly Figure objects

    Raises:
    - ValueError: if the phase column is not found in df
    """
    # enforce phase column
    if phase_col not in df.columns:
        raise ValueError(f"Required phase column '{phase_col}' not found in dataframe")

    # auto-detect features if not provided
    if features is None:
        exclude = {phase_col, subject_col, task_col}
        features = [c for c in df.columns if c not in exclude and pd.api.types.is_numeric_dtype(df[c])]

    figs = {}
    for task in df[task_col].unique():
        task_df = df[df[task_col] == task]
        subjects = task_df[subject_col].unique()

        # compute mean and std across subjects for each phase point
        mean_df = task_df.groupby(phase_col)[features].mean()
        std_df = task_df.groupby(phase_col)[features].std()

        fig = go.Figure()
        # spaghetti traces
        for subj in subjects:
            subj_df = task_df[task_df[subject_col] == subj]
            for feat in features:
                fig.add_trace(go.Scatter(
                    x=subj_df[phase_col], y=subj_df[feat],
                    mode='lines',
                    name=f'{subj} - {feat}',
                    visible=False,
                    line=dict(width=1)
                ))

        # mean + std traces
        for feat in features:
            # mean line
            fig.add_trace(go.Scatter(
                x=mean_df.index, y=mean_df[feat],
                mode='lines',
                name=f'Mean {feat}',
                visible=True,
                line=dict(width=2)
            ))
            # +1 SD line (invisible legend)
            fig.add_trace(go.Scatter(
                x=mean_df.index, y=mean_df[feat] + std_df[feat],
                mode='lines',
                showlegend=False,
                visible=True,
                line=dict(width=0)
            ))
            # -1 SD fill
            fig.add_trace(go.Scatter(
                x=mean_df.index, y=mean_df[feat] - std_df[feat],
                mode='lines',
                showlegend=False,
                visible=True,
                fill='tonexty',
                line=dict(width=0)
            ))

        # configure toggle buttons
        n_spaghetti = len(subjects) * len(features)
        n_meanstd = len(features) * 3  # mean, +sd, -sd
        mean_mask = [False] * n_spaghetti + [True] * n_meanstd
        spaghetti_mask = [True] * n_spaghetti + [False] * n_meanstd

        fig.update_layout(
            updatemenus=[dict(
                type='buttons',
                direction='right',
                buttons=[
                    dict(label='Mean + STD', method='update', args=[{'visible': mean_mask}, {'title': f'{task} - Mean + STD'}]),
                    dict(label='Spaghetti', method='update', args=[{'visible': spaghetti_mask}, {'title': f'{task} - Spaghetti'}])
                ],
                pad={'r': 10, 't': 10},
                showactive=True
            )],
            title=f'{task} - Mean + STD',
            xaxis_title=f'{phase_col} (%)',
            yaxis_title='Feature Value'
        )

        figs[task] = fig

    return figs


if __name__ == '__main__':
    import argparse
    import os
    # for file dialog
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        tk = None
        filedialog = None

    parser = argparse.ArgumentParser(
        description='Visualize standardized locomotion phase-indexed dataframe.')
    parser.add_argument('--input_parquet', nargs='?', help='Path to standardized Parquet file')
    parser.add_argument('--phase_col', default='phase_%', help='Name of the phase column (required)')
    parser.add_argument('--subject_col', default='subject_id', help='Name of the subject identifier column')
    parser.add_argument('--task_col', default='task_name', help='Name of the task identifier column')
    parser.add_argument('--features', nargs='+', help='List of feature columns to plot')
    parser.add_argument('--output_html', help='If provided, save all task figures to this HTML file')
    args = parser.parse_args()

    # determine input file via argument or file dialog
    input_file = None
    if args.input_parquet:
        input_file = args.input_parquet
    else:
        if tk and filedialog:
            root = tk.Tk()
            root.withdraw()
            files = filedialog.askopenfilenames(
                title='Select Parquet Files',
                filetypes=[('Parquet files', '*.parquet'), ('All files', '*.*')]
            )
            if files:
                input_file = files[0]
        else:
            parser.error('No input_parquet provided and tkinter not available for file dialog')

    if not input_file or not os.path.exists(input_file):
        parser.error(f'Input file "{input_file}" does not exist')

    df = pd.read_parquet(input_file)
    figs = visualize_tasks(
        df,
        phase_col=args.phase_col,
        subject_col=args.subject_col,
        task_col=args.task_col,
        features=args.features
    )

    # save or show
    if args.output_html:
        plotly_plot(list(figs.values()), filename=args.output_html, auto_open=False)
    else:
        first_fig = next(iter(figs.values()), None)
        if first_fig:
            first_fig.show()
