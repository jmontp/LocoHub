function exportFigure(fig, savePath, varargin)
    % EXPORTFIGURE - Export figure with proper DPI and formats
    %
    % Inputs:
    %   fig - Figure handle
    %   savePath - Base path for saving (without extension)
    %   Optional name-value pairs:
    %     'Format' - Cell array of formats (default: {'png', 'pdf'})
    %     'DPI' - Resolution for raster formats (default: 300)
    %     'Theme' - Theme struct for sizing
    
    % Parse inputs
    p = inputParser;
    addParameter(p, 'Format', {{'png', 'pdf'}}, @iscell);
    addParameter(p, 'DPI', 300, @isnumeric);
    addParameter(p, 'Theme', struct(), @isstruct);
    parse(p, varargin{:});
    
    formats = p.Results.Format;
    dpi = p.Results.DPI;
    theme = p.Results.Theme;
    
    % Ensure formats is a cell array
    if ischar(formats)
        formats = {formats};
    elseif iscell(formats) && iscell(formats{1})
        formats = formats{1};
    end
    
    % Set paper properties for consistent sizing
    set(fig, 'PaperPositionMode', 'auto');
    set(fig, 'PaperUnits', 'inches');
    
    for i = 1:length(formats)
        format = formats{i};
        filename = sprintf('%s.%s', savePath, format);
        
        switch lower(format)
            case 'png'
                print(fig, filename, '-dpng', sprintf('-r%d', dpi));
                
            case 'pdf'
                print(fig, filename, '-dpdf', '-bestfit');
                
            case 'eps'
                print(fig, filename, '-depsc2', '-tiff');
                
            case 'svg'
                print(fig, filename, '-dsvg');
                
            case 'tiff' 
                print(fig, filename, '-dtiff', sprintf('-r%d', dpi));
                
            otherwise
                warning('Unknown format: %s', format);
        end
        
        fprintf('Figure saved: %s\n', filename);
    end
end