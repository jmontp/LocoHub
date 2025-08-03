function theme = getBiomechTheme(varargin)
    % GETBIOMECHTHEME - Get biomechanics-specific theme settings
    %
    % Inputs:
    %   Optional name-value pairs:
    %     'Style' - 'publication', 'presentation', or 'manuscript' (default: 'publication')
    %     'FontSize' - Base font size (default: 12)
    %     'LineWidth' - Base line width (default: 1.5)
    %
    % Returns:
    %   theme - Struct with theme settings
    
    % Parse inputs
    p = inputParser;
    addParameter(p, 'Style', 'publication', @ischar);
    addParameter(p, 'FontSize', 12, @isnumeric);
    addParameter(p, 'LineWidth', 1.5, @isnumeric);
    parse(p, varargin{:});
    
    style = p.Results.Style;
    baseFontSize = p.Results.FontSize;
    baseLineWidth = p.Results.LineWidth;
    
    % Base theme settings
    theme = struct();
    theme.style = style;
    
    % Typography
    switch lower(style)
        case 'publication'
            theme.font.family = 'Arial';
            theme.font.size.title = baseFontSize + 2;
            theme.font.size.axis = baseFontSize;
            theme.font.size.label = baseFontSize;
            theme.font.size.legend = baseFontSize - 1;
            theme.font.weight.title = 'bold';
            theme.font.weight.axis = 'normal';
            
        case 'presentation'
            theme.font.family = 'Arial';
            theme.font.size.title = baseFontSize + 4;
            theme.font.size.axis = baseFontSize + 2;
            theme.font.size.label = baseFontSize + 2;
            theme.font.size.legend = baseFontSize;
            theme.font.weight.title = 'bold';
            theme.font.weight.axis = 'bold';
            
        case 'manuscript'
            theme.font.family = 'Times New Roman';
            theme.font.size.title = baseFontSize + 1;
            theme.font.size.axis = baseFontSize - 1;
            theme.font.size.label = baseFontSize - 1;
            theme.font.size.legend = baseFontSize - 2;
            theme.font.weight.title = 'bold';
            theme.font.weight.axis = 'normal';
    end
    
    % Lines and markers
    theme.line.width.main = baseLineWidth;
    theme.line.width.thin = baseLineWidth * 0.7;
    theme.line.width.thick = baseLineWidth * 1.5;
    theme.line.width.grid = 0.5;
    
    % Colors (defined using hex codes for consistency)
    theme.colors = getBiomechColors();
    
    % Layout
    theme.layout.margin = [0.08, 0.08, 0.08, 0.08]; % [left, bottom, right, top]
    theme.layout.spacing = 0.05;
    theme.layout.panel_background = [1, 1, 1]; % White
    theme.layout.grid_color = [0.9, 0.9, 0.9]; % Light gray
    theme.layout.grid_alpha = 0.7;
    
    % Axis formatting
    theme.axis.color = [0.2, 0.2, 0.2]; % Dark gray
    theme.axis.tick_length = 0.01;
    theme.axis.show_box = true;
    theme.axis.show_grid = true;
    
    % Legend
    theme.legend.location = 'northeast';
    theme.legend.frame = true;
    theme.legend.background = [1, 1, 1, 0.9]; % Semi-transparent white
end