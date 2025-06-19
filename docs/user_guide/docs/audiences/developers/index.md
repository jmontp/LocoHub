# For Software Developers

**Build biomechanical applications with standardized data infrastructure.**

<div class="developer-hero" markdown>

## :material-code-braces: **Developer-First Biomechanics Platform**

Integrate production-ready gait analysis into your applications. Clean APIs, comprehensive documentation, and battle-tested data validation for reliable biomechanical software.

[**:material-rocket-launch: Quick Integration**](../../getting_started/quick_start/){ .md-button .md-button--primary }
[**:material-api: API Documentation**](../../reference/api_reference/){ .md-button }

</div>

## :material-lightning-bolt: Why Developers Choose Our Platform

<div class="developer-benefits" markdown>

### :material-api: **Clean, Consistent APIs**
**No biomechanics expertise required.** Simple, well-documented interfaces abstract away domain complexity while preserving analytical power.

### :material-database-check: **Built-in Data Validation**  
**50+ biomechanical validation rules included.** Automatic quality checks ensure physiologically plausible data in your applications.

### :material-package-variant: **Multiple Language Support**
**Python and MATLAB libraries with identical APIs.** Choose your preferred development environment without feature compromises.

### :material-speedometer: **Production-Ready Performance**
**Optimized for large datasets and real-time applications.** Memory-efficient operations handle thousands of gait cycles without performance degradation.

</div>

## :material-code-tags: Integration Examples

<div class="integration-examples" markdown>

### **Web Application Integration**

=== "Python Flask API"

    ```python
    from flask import Flask, request, jsonify
    from locomotion_analysis import LocomotionData
    import numpy as np
    
    app = Flask(__name__)
    
    @app.route('/api/gait-analysis', methods=['POST'])
    def analyze_gait():
        try:
            # Load uploaded data
            data_file = request.files['gait_data']
            data = LocomotionData.from_file(data_file)
            
            # Validate data quality
            validation_results = data.validate()
            if not validation_results.is_valid:
                return jsonify({
                    'error': 'Data validation failed',
                    'details': validation_results.errors
                }), 400
            
            # Perform analysis
            results = {
                'subjects': data.get_subject_count(),
                'tasks': data.get_task_list(),
                'quality_score': validation_results.overall_score,
                'key_metrics': {
                    'knee_rom_avg': float(np.degrees(data.calculate_rom('knee_flexion_angle_ipsi_rad').mean())),
                    'cadence_avg': float(data.calculate_cadence().mean()),
                    'stride_length_avg': float(data.calculate_stride_length().mean())
                }
            }
            
            return jsonify(results)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    if __name__ == '__main__':
        app.run(debug=True)
    ```

=== "React Frontend Integration"

    ```javascript
    import React, { useState } from 'react';
    import axios from 'axios';
    
    const GaitAnalysisUpload = () => {
        const [file, setFile] = useState(null);
        const [results, setResults] = useState(null);
        const [loading, setLoading] = useState(false);
        const [error, setError] = useState(null);
        
        const handleFileUpload = async (event) => {
            event.preventDefault();
            if (!file) return;
            
            setLoading(true);
            setError(null);
            
            const formData = new FormData();
            formData.append('gait_data', file);
            
            try {
                const response = await axios.post('/api/gait-analysis', formData, {
                    headers: {
                        'Content-Type': 'multipart/form-data',
                    },
                });
                
                setResults(response.data);
            } catch (err) {
                setError(err.response?.data?.error || 'Analysis failed');
            } finally {
                setLoading(false);
            }
        };
        
        return (
            <div className="gait-analysis-upload">
                <form onSubmit={handleFileUpload}>
                    <input
                        type="file"
                        accept=".parquet,.csv"
                        onChange={(e) => setFile(e.target.files[0])}
                    />
                    <button type="submit" disabled={!file || loading}>
                        {loading ? 'Analyzing...' : 'Analyze Gait Data'}
                    </button>
                </form>
                
                {error && <div className="error">{error}</div>}
                
                {results && (
                    <div className="results">
                        <h3>Analysis Results</h3>
                        <p>Subjects: {results.subjects}</p>
                        <p>Tasks: {results.tasks.join(', ')}</p>
                        <p>Quality Score: {(results.quality_score * 100).toFixed(1)}%</p>
                        <div className="metrics">
                            <h4>Key Metrics</h4>
                            <p>Knee ROM: {results.key_metrics.knee_rom_avg.toFixed(1)}°</p>
                            <p>Cadence: {results.key_metrics.cadence_avg.toFixed(1)} steps/min</p>
                            <p>Stride Length: {results.key_metrics.stride_length_avg.toFixed(2)}m</p>
                        </div>
                    </div>
                )}
            </div>
        );
    };
    
    export default GaitAnalysisUpload;
    ```

=== "MATLAB Desktop Integration"

    ```matlab
    function results = integrateGaitAnalysis(dataPath)
        % INTEGRATEGAITANALYSIS Integrate gait analysis into MATLAB application
        %
        % Usage:
        %   results = integrateGaitAnalysis('path/to/gait_data.parquet');
        
        try
            % Load and validate data
            data = LocomotionData(dataPath);
            validation = data.validate();
            
            if ~validation.isValid
                error('Data validation failed: %s', strjoin(validation.errors, ', '));
            end
            
            % Extract key metrics
            results = struct();
            results.subjects = data.getSubjectCount();
            results.tasks = data.getTaskList();
            results.qualityScore = validation.overallScore;
            
            % Calculate biomechanical metrics
            results.metrics = struct();
            results.metrics.kneeRomAvg = rad2deg(mean(data.calculateRom('knee_flexion_angle_ipsi_rad')));
            results.metrics.cadenceAvg = mean(data.calculateCadence());
            results.metrics.strideLengthAvg = mean(data.calculateStrideLength());
            
            % Generate visualization
            figure('Name', 'Gait Analysis Results');
            data.plotAverageTrajectory('knee_flexion_angle_ipsi_rad', 'level_walking');
            
            fprintf('Analysis completed successfully.\n');
            fprintf('Quality Score: %.1f%%\n', results.qualityScore * 100);
            fprintf('Knee ROM: %.1f degrees\n', results.metrics.kneeRomAvg);
            
        catch ME
            fprintf('Error in gait analysis: %s\n', ME.message);
            results = [];
        end
    end
    ```

**Output:** Robust gait analysis integration with error handling and validation

</div>

## :material-api: API Architecture

<div class="api-architecture" markdown>

### **Core Classes and Methods**

| Class | Purpose | Key Methods |
|-------|---------|-------------|
| `LocomotionData` | Main data container | `filter()`, `validate()`, `calculate_*()` |
| `DataValidator` | Quality assurance | `validate_biomechanics()`, `check_ranges()` |
| `FeatureExtractor` | Metric calculation | `extract_temporal()`, `extract_kinematic()` |
| `Visualizer` | Plotting utilities | `plot_trajectory()`, `plot_comparison()` |

### **Data Flow Architecture**

```mermaid
graph TD
    A[Raw Data] --> B[LocomotionData.load()]
    B --> C[DataValidator.validate()]
    C --> D{Valid?}
    D -->|Yes| E[Analysis Methods]
    D -->|No| F[Error Response]
    E --> G[FeatureExtractor.extract()]
    G --> H[Results/Visualizations]
```

### **Error Handling Strategy**

```python
# Comprehensive error handling example
class GaitAnalysisError(Exception):
    """Custom exception for gait analysis errors"""
    pass

def robust_gait_analysis(data_path):
    try:
        # Load data with validation
        data = LocomotionData(data_path)
        
        # Validate data quality
        validation = data.validate()
        if not validation.is_valid:
            raise GaitAnalysisError(f"Validation failed: {validation.get_error_summary()}")
        
        # Perform analysis with error checking
        results = {}
        
        # Safe metric calculation
        try:
            results['knee_rom'] = data.calculate_rom('knee_flexion_angle_ipsi_rad')
        except KeyError as e:
            results['knee_rom'] = None
            results['warnings'] = f"Knee ROM calculation failed: {e}"
        
        return {
            'success': True,
            'data': results,
            'quality_score': validation.overall_score
        }
        
    except FileNotFoundError:
        return {'success': False, 'error': 'Data file not found'}
    except GaitAnalysisError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {str(e)}'}
```

</div>

## :material-database: Developer Resources

<div name="developer-resources" markdown>

### **Libraries and SDKs**

| Package | Language | Installation | Documentation |
|---------|----------|--------------|---------------|
| `locomotion-analysis` | Python | `pip install locomotion-analysis` | [Python API Reference](../../reference/api_reference/) |
| `LocomotionData.m` | MATLAB | Add to path | [MATLAB Documentation](../../tutorials/matlab/) |

### **Sample Applications**

| Application Type | Repository | Description |
|------------------|------------|-------------|
| **Web Dashboard** | [gait-analysis-dashboard](https://github.com/your-org/gait-analysis-dashboard) | React + Flask web application |
| **CLI Tool** | [gait-analysis-cli](https://github.com/your-org/gait-analysis-cli) | Command-line batch processing |
| **Jupyter Integration** | [gait-analysis-notebooks](https://github.com/your-org/gait-analysis-notebooks) | Interactive analysis examples |

### **Development Tools**

- :material-test-tube: **[Test Suite](https://github.com/your-org/locomotion-data-standardization/tree/main/tests)** - Comprehensive validation tests
- :material-docker: **[Docker Images](https://hub.docker.com/r/your-org/locomotion-analysis)** - Containerized deployment
- :material-github-actions: **[CI/CD Templates](https://github.com/your-org/locomotion-data-standardization/tree/main/.github)** - Automated testing workflows

</div>

## :material-cog: Development Pathways

<div class="development-paths" markdown>

<div class="path-card web-dev" markdown>

### :material-web: **Web Application Development**

**Perfect for:** Clinical dashboards, research portals, patient interfaces

**Development Stack:**
1. [API Integration](../../getting_started/quick_start/) - Connect to analysis backend
2. [Data Validation](../../reference/api_reference/) - Implement quality checks
3. [Visualization Components](web-visualization/) - Interactive plotting
4. [Deployment Guide](web-deployment/) - Production setup

**Key Technologies:**
- REST API endpoints for analysis operations
- WebSocket support for real-time processing
- JSON data exchange with validation schemas
- Responsive visualization components

[**Start Web Development :material-arrow-right:**](web-development/){ .md-button .developer-button }

</div>

<div class="path-card desktop-dev" markdown>

### :material-desktop-classic: **Desktop Application Development**

**Perfect for:** Clinical software, research tools, standalone analysis

**Development Stack:**
1. [Library Integration](desktop-integration/) - Embed analysis capabilities
2. [GUI Development](desktop-gui/) - User interface design
3. [Data Management](desktop-data/) - File handling and storage
4. [Distribution](desktop-deployment/) - Packaging and installation

**Key Technologies:**
- Native Python/MATLAB integration
- Cross-platform GUI frameworks
- Efficient data processing and caching
- Professional installer packages

[**Start Desktop Development :material-arrow-right:**](desktop-development/){ .md-button .developer-button }

</div>

<div class="path-card mobile-dev" markdown>

### :material-cellphone: **Mobile Application Development**

**Perfect for:** Field data collection, patient monitoring, portable analysis

**Development Stack:**
1. [API Integration](mobile-api/) - Cloud-based analysis backend
2. [Data Collection](mobile-sensors/) - Device sensor integration
3. [Offline Capabilities](mobile-offline/) - Local processing options
4. [Cloud Sync](mobile-sync/) - Data synchronization

**Key Technologies:**
- RESTful API consumption
- Local data storage and caching
- Sensor data integration (accelerometer, gyroscope)
- Cloud synchronization and backup

[**Start Mobile Development :material-arrow-right:**](mobile-development/){ .md-button .developer-button }

</div>

</div>

## :material-rocket-launch: Developer Quick Start

<div class="getting-started-developer" markdown>

### **Choose Your Development Approach**

=== ":material-timer: Rapid Prototyping (30 minutes)"

    **Perfect for:** Proof of concept, API exploration
    
    1. Install development libraries (5 min)
    2. Load sample dataset (5 min)
    3. Implement basic analysis (15 min)
    4. Create simple visualization (5 min)
    
    **Outcome:** Working prototype with core functionality
    
    [:material-rocket-launch: Quick Prototype](../../getting_started/quick_start/){ .md-button .md-button--primary }

=== ":material-application: Full Application (2-4 hours)"

    **Perfect for:** Production applications, comprehensive features
    
    1. Set up development environment (30 min)
    2. Implement data validation and error handling (60 min)
    3. Build user interface components (90 min)
    4. Add testing and documentation (60 min)
    
    **Outcome:** Production-ready application with full features
    
    [:material-book-open: Full Development Guide](../../tutorials/){ .md-button }

=== ":material-cloud: Cloud Deployment (ongoing)"

    **Perfect for:** Scalable applications, multi-user systems
    
    1. Container setup and orchestration
    2. Database integration and optimization
    3. Load balancing and scaling configuration
    4. Monitoring and logging implementation
    
    **Outcome:** Cloud-native biomechanical analysis platform
    
    [:material-cloud: Cloud Guide](cloud-deployment/){ .md-button }

</div>

## :material-help-circle: Developer Support

<div class="developer-support" markdown>

**Development Resources:**

- :material-book-code: **[API Reference](../../reference/api_reference/)** - Complete method documentation
- :material-github: **[Source Code](https://github.com/your-org/locomotion-data-standardization)** - Open source implementation
- :material-test-tube: **[Testing Framework](testing-guide/)** - Unit and integration tests
- :material-docker: **[Deployment Tools](deployment-tools/)** - Docker, CI/CD, monitoring
- :material-bug: **[Issue Tracking](https://github.com/your-org/locomotion-data-standardization/issues)** - Bug reports and feature requests

**Development Support:**
- Comprehensive API documentation with examples
- Sample applications and integration patterns
- Performance optimization guidelines
- Security best practices and guidelines

</div>

---

<div class="developer-cta" markdown>

## Ready to Build Biomechanical Applications?

**Integrate production-ready gait analysis with clean APIs and comprehensive documentation.**

[**:material-rocket-launch: Start Development**](../../getting_started/quick_start/){ .md-button .md-button--primary .cta-button }
[**:material-api: Explore API**](../../reference/api_reference/){ .md-button .cta-button }

*Build powerful biomechanical applications with developer-first tools.*

</div>