function colors = getBiomechColors(varargin)
    % GETBIOMECHCOLORS - Get colorblind-friendly color palettes for biomechanical data
    %
    % Inputs:
    %   Optional name-value pairs:
    %     'Palette' - 'default', 'joints', 'tasks', 'subjects', or 'sequential' (default: 'default')
    %     'ColorblindSafe' - true/false (default: true)
    %
    % Returns:
    %   colors - Struct with color definitions
    
    % Parse inputs
    p = inputParser;
    addParameter(p, 'Palette', 'default', @ischar);
    addParameter(p, 'ColorblindSafe', true, @islogical);
    parse(p, varargin{:});
    
    palette = p.Results.Palette;
    colorblindSafe = p.Results.ColorblindSafe;
    
    colors = struct();
    
    if colorblindSafe
        % Colorblind-friendly palettes based on ColorBrewer and Viridis
        switch lower(palette)
            case 'default'
                colors.primary = [0.12, 0.47, 0.71];    % Blue
                colors.secondary = [0.89, 0.47, 0.00];  % Orange
                colors.tertiary = [0.17, 0.63, 0.17];   % Green
                colors.quaternary = [0.84, 0.19, 0.15]; % Red
                colors.quinary = [0.58, 0.40, 0.74];    % Purple
                colors.senary = [0.55, 0.34, 0.29];     % Brown
                
            case 'joints'
                % Optimized for hip-knee-ankle visualization
                colors.hip = [0.89, 0.47, 0.00];        % Orange
                colors.knee = [0.12, 0.47, 0.71];       % Blue  
                colors.ankle = [0.17, 0.63, 0.17];      % Green
                colors.hip_light = [0.99, 0.75, 0.44];  % Light orange
                colors.knee_light = [0.68, 0.85, 0.90]; % Light blue
                colors.ankle_light = [0.78, 0.91, 0.78]; % Light green
                
            case 'tasks'
                % Optimized for different locomotor tasks
                colors.normal_walk = [0.12, 0.47, 0.71]; % Blue
                colors.fast_walk = [0.20, 0.63, 0.17];   % Green
                colors.slow_walk = [0.65, 0.81, 0.89];   % Light blue
                colors.incline_walk = [0.89, 0.47, 0.00]; % Orange
                colors.decline_walk = [0.99, 0.75, 0.44]; % Light orange
                colors.stair_ascent = [0.84, 0.19, 0.15]; % Red
                colors.stair_descent = [0.99, 0.68, 0.68]; % Light red
                colors.run = [0.58, 0.40, 0.74];         % Purple
                
            case 'subjects'
                % For population studies - using qualitative palette
                colors.subject_palette = [
                    0.12, 0.47, 0.71;  % Blue
                    0.89, 0.47, 0.00;  % Orange
                    0.17, 0.63, 0.17;  % Green
                    0.84, 0.19, 0.15;  % Red
                    0.58, 0.40, 0.74;  % Purple
                    0.55, 0.34, 0.29;  % Brown
                    0.89, 0.47, 0.76;  % Pink
                    0.50, 0.50, 0.50   % Gray
                ];
                
            case 'sequential'
                % For continuous data or phases
                colors.sequential_blue = [
                    0.97, 0.98, 1.00;
                    0.87, 0.92, 0.97;
                    0.68, 0.85, 0.90;
                    0.45, 0.68, 0.82;
                    0.21, 0.51, 0.74;
                    0.08, 0.35, 0.55;
                    0.03, 0.19, 0.38
                ];
        end
    else
        % Standard palette (not colorblind optimized)
        colors.primary = [0, 0.45, 0.74];
        colors.secondary = [0.85, 0.33, 0.10];
        colors.tertiary = [0.93, 0.69, 0.13];
        % ... additional standard colors
    end
    
    % Special biomechanical colors
    colors.valid_cycle = [0.3, 0.3, 0.3];        % Dark gray for valid data
    colors.invalid_cycle = [0.84, 0.19, 0.15];   % Red for invalid/outlier data
    colors.mean_line = [0.12, 0.47, 0.71];       % Blue for mean patterns
    colors.confidence_band = [0.68, 0.85, 0.90]; % Light blue for confidence
    colors.phase_annotation = [0.5, 0.5, 0.5];   % Gray for phase markers
    
    % Transparency values
    colors.alpha.cycle = 0.3;
    colors.alpha.confidence = 0.4;
    colors.alpha.background = 0.1;
end