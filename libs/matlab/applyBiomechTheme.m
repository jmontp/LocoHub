function applyBiomechTheme(fig, theme)
    % APPLYBIOMECHTHEME - Apply biomechanics theme to existing figure
    %
    % Inputs:
    %   fig - Figure handle
    %   theme - Theme struct from getBiomechTheme()
    
    if nargin < 2
        theme = getBiomechTheme();
    end
    
    % Set current figure
    figure(fig);
    
    % Get all axes in figure
    axes_handles = findall(fig, 'Type', 'axes');
    
    for ax = axes_handles'
        % Font settings
        set(ax, 'FontName', theme.font.family);
        set(ax, 'FontSize', theme.font.size.axis);
        
        % Axis colors and styling
        set(ax, 'XColor', theme.axis.color);
        set(ax, 'YColor', theme.axis.color);
        set(ax, 'LineWidth', theme.line.width.thin);
        
        % Grid settings
        if theme.axis.show_grid
            grid(ax, 'on');
            set(ax, 'GridColor', theme.layout.grid_color);
            set(ax, 'GridAlpha', theme.layout.grid_alpha);
            set(ax, 'GridLineStyle', '-');
        end
        
        % Background
        set(ax, 'Color', theme.layout.panel_background);
        
        % Box
        if theme.axis.show_box
            box(ax, 'on');
        end
        
        % Title formatting
        title_handle = get(ax, 'Title');
        if ~isempty(title_handle.String)
            set(title_handle, 'FontSize', theme.font.size.title);
            set(title_handle, 'FontWeight', theme.font.weight.title);
        end
        
        % Label formatting
        xlabel_handle = get(ax, 'XLabel');
        ylabel_handle = get(ax, 'YLabel');
        set(xlabel_handle, 'FontSize', theme.font.size.label);
        set(ylabel_handle, 'FontSize', theme.font.size.label);
    end
    
    % Set figure background
    set(fig, 'Color', 'white');
    
    % Apply to legend if present
    legend_handles = findall(fig, 'Type', 'legend');
    for leg = legend_handles'
        set(leg, 'FontSize', theme.font.size.legend);
        set(leg, 'Location', theme.legend.location);
        if theme.legend.frame
            set(leg, 'Box', 'on');
        end
    end
end