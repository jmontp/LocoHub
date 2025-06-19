# Integration Guides

Comprehensive guides for integrating the locomotion data standardization platform into larger systems and research workflows.

## Quick Navigation

- **[ML Pipeline Integration](ml-pipeline-integration.md)** - Machine learning workflow integration
- **[Research Platform Integration](research-platform-integration.md)** - Integration with research platforms
- **[Performance Optimization](performance-optimization.md)** - Large dataset optimization strategies
- **[Cloud Integration](cloud-integration.md)** - Cloud platform deployment patterns

## Integration Overview

The platform provides flexible APIs for integration into various environments:

### Core Integration Points

1. **Data Analysis**: `LocomotionData` class for efficient biomechanical analysis
2. **Validation**: `DatasetValidator` for quality assessment and compliance
3. **Batch Processing**: CLI tools for large-scale data processing
4. **Visualization**: Automated plot generation and validation reports

### Common Integration Patterns

#### Research Pipeline Integration
```python
# Standard research workflow integration
from lib.core.locomotion_analysis import LocomotionData
from lib.validation.dataset_validator_phase import DatasetValidator

# 1. Load and validate data
validator = DatasetValidator('study_data_phase.parquet')
report_path = validator.run_validation()

# 2. Load for analysis
loco = LocomotionData('study_data_phase.parquet')

# 3. Extract features for analysis
features_matrix = []
for subject in loco.subjects:
    data_3d, features = loco.get_cycles(subject, 'level_walking')
    if data_3d is not None:
        mean_pattern = np.mean(data_3d, axis=0)  # (150, n_features)
        features_matrix.append(mean_pattern.flatten())

features_matrix = np.array(features_matrix)  # (n_subjects, 150*n_features)
```

#### Production System Integration
```python
# Production system with error handling and monitoring
import logging
from pathlib import Path

class LocomotionAnalysisService:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def process_dataset(self, dataset_path: str) -> Dict:
        try:
            # Validate first
            validator = DatasetValidator(dataset_path, generate_plots=False)
            locomotion_data = validator.load_dataset()
            validation_results = validator.validate_dataset(locomotion_data)
            
            # Check quality threshold
            quality_score = validation_results['valid_steps'] / validation_results['total_steps']
            if quality_score < self.config['min_quality_threshold']:
                return {'status': 'REJECTED', 'quality_score': quality_score}
            
            # Process for downstream analysis
            analysis_results = self._extract_analysis_features(locomotion_data)
            
            return {
                'status': 'SUCCESS',
                'quality_score': quality_score,
                'analysis_results': analysis_results,
                'validation_report': validation_results
            }
            
        except Exception as e:
            self.logger.error(f"Processing failed for {dataset_path}: {e}")
            return {'status': 'ERROR', 'error': str(e)}
```

## Integration Architectures

### Microservices Architecture

```python
# Example microservice for locomotion data processing
from fastapi import FastAPI, UploadFile, HTTPException
from typing import Dict, List
import tempfile
import os

app = FastAPI(title="Locomotion Data Service")

@app.post("/validate-dataset")
async def validate_dataset(file: UploadFile) -> Dict:
    """Validate uploaded locomotion dataset."""
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # Validate dataset
        validator = DatasetValidator(tmp_path, generate_plots=False)
        locomotion_data = validator.load_dataset()
        results = validator.validate_dataset(locomotion_data)
        
        # Return validation summary
        return {
            'filename': file.filename,
            'total_steps': results['total_steps'],
            'valid_steps': results['valid_steps'],
            'quality_score': results['valid_steps'] / results['total_steps'],
            'tasks': results['tasks_validated'],
            'failure_count': len(results['kinematic_failures']) + len(results['kinetic_failures'])
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        os.unlink(tmp_path)

@app.post("/analyze-gait-patterns")
async def analyze_gait_patterns(file: UploadFile, subjects: List[str] = None) -> Dict:
    """Extract gait pattern analysis from dataset."""
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        loco = LocomotionData(tmp_path)
        
        # Filter subjects if specified
        target_subjects = subjects if subjects else loco.subjects[:10]  # Limit for demo
        
        analysis_results = {}
        for subject in target_subjects:
            if subject in loco.subjects:
                # Get mean patterns for level walking
                mean_patterns = loco.get_mean_patterns(subject, 'level_walking')
                rom_data = loco.calculate_rom(subject, 'level_walking', by_cycle=False)
                
                analysis_results[subject] = {
                    'mean_patterns': {k: v.tolist() for k, v in mean_patterns.items()},
                    'rom': rom_data
                }
        
        return {
            'filename': file.filename,
            'subjects_analyzed': len(analysis_results),
            'analysis_results': analysis_results
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        os.unlink(tmp_path)
```

### Event-Driven Architecture

```python
# Event-driven processing with message queues
import json
from typing import Dict, Any
import redis
from celery import Celery

# Celery setup for distributed processing
app = Celery('locomotion_processing')
app.config_from_object('celeryconfig')

# Redis for result storage
redis_client = redis.Redis(host='localhost', port=6379, db=0)

@app.task
def process_locomotion_dataset(dataset_info: Dict[str, Any]) -> str:
    """Celery task for processing locomotion datasets."""
    
    dataset_path = dataset_info['path']
    processing_id = dataset_info['id']
    
    try:
        # Update status
        redis_client.hset(f"processing:{processing_id}", "status", "PROCESSING")
        
        # Validate dataset
        validator = DatasetValidator(dataset_path, generate_plots=False)
        locomotion_data = validator.load_dataset()
        validation_results = validator.validate_dataset(locomotion_data)
        
        # Extract analysis features
        analysis_results = extract_locomotion_features(locomotion_data)
        
        # Store results
        results = {
            'validation': validation_results,
            'analysis': analysis_results,
            'status': 'COMPLETED'
        }
        
        redis_client.hset(f"processing:{processing_id}", "results", json.dumps(results))
        redis_client.hset(f"processing:{processing_id}", "status", "COMPLETED")
        
        return processing_id
        
    except Exception as e:
        error_info = {'status': 'ERROR', 'error': str(e)}
        redis_client.hset(f"processing:{processing_id}", "results", json.dumps(error_info))
        redis_client.hset(f"processing:{processing_id}", "status", "ERROR")
        raise

def extract_locomotion_features(locomotion_data: LocomotionData) -> Dict:
    """Extract standardized features for downstream analysis."""
    
    features = {
        'dataset_info': {
            'subjects': len(locomotion_data.subjects),
            'tasks': len(locomotion_data.tasks),
            'features': len(locomotion_data.features)
        },
        'subject_features': {}
    }
    
    for subject in locomotion_data.subjects:
        subject_data = {}
        
        for task in locomotion_data.tasks:
            # Get 3D data
            data_3d, feature_names = locomotion_data.get_cycles(subject, task)
            
            if data_3d is not None:
                # Calculate summary statistics
                mean_patterns = np.mean(data_3d, axis=0)  # (150, n_features)
                std_patterns = np.std(data_3d, axis=0)
                
                # Calculate ROM
                rom_per_cycle = np.max(data_3d, axis=1) - np.min(data_3d, axis=1)
                mean_rom = np.mean(rom_per_cycle, axis=0)
                
                subject_data[task] = {
                    'n_cycles': data_3d.shape[0],
                    'mean_patterns': mean_patterns.tolist(),
                    'std_patterns': std_patterns.tolist(),
                    'mean_rom': mean_rom.tolist(),
                    'feature_names': feature_names
                }
        
        features['subject_features'][subject] = subject_data
    
    return features

# Usage: Submit processing job
dataset_info = {
    'id': 'proc_001',
    'path': '/data/study_dataset_phase.parquet',
    'user_id': 'researcher_123'
}

task = process_locomotion_dataset.delay(dataset_info)
print(f"Processing job submitted: {task.id}")
```

## Database Integration

### SQL Database Integration

```python
# Integration with SQL databases for metadata storage
import sqlite3
import pandas as pd
from datetime import datetime
from typing import Optional

class LocomotionDataManager:
    """Database-backed locomotion data management."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS datasets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    file_path TEXT NOT NULL,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    validation_status TEXT,
                    quality_score REAL,
                    subject_count INTEGER,
                    task_count INTEGER,
                    total_steps INTEGER
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS validation_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dataset_id INTEGER,
                    validation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    validation_type TEXT,
                    total_failures INTEGER,
                    report_path TEXT,
                    FOREIGN KEY (dataset_id) REFERENCES datasets (id)
                )
            """)
    
    def register_dataset(self, name: str, file_path: str) -> int:
        """Register new dataset and validate."""
        
        try:
            # Validate dataset
            validator = DatasetValidator(file_path, generate_plots=False)
            locomotion_data = validator.load_dataset()
            validation_results = validator.validate_dataset(locomotion_data)
            
            quality_score = validation_results['valid_steps'] / validation_results['total_steps']
            
            # Store in database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO datasets 
                    (name, file_path, validation_status, quality_score, subject_count, task_count, total_steps)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    name, file_path, 'VALIDATED', quality_score,
                    len(locomotion_data.subjects), len(locomotion_data.tasks),
                    validation_results['total_steps']
                ))
                
                dataset_id = cursor.lastrowid
                
                # Store validation details
                total_failures = len(validation_results['kinematic_failures']) + len(validation_results['kinetic_failures'])
                conn.execute("""
                    INSERT INTO validation_results 
                    (dataset_id, validation_type, total_failures)
                    VALUES (?, ?, ?)
                """, (dataset_id, 'FULL', total_failures))
            
            return dataset_id
            
        except Exception as e:
            # Store failed validation
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO datasets 
                    (name, file_path, validation_status, quality_score)
                    VALUES (?, ?, ?, ?)
                """, (name, file_path, 'FAILED', 0.0))
                
                return cursor.lastrowid
    
    def get_dataset_info(self, dataset_id: int) -> Optional[Dict]:
        """Get dataset information."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM datasets WHERE id = ?
            """, (dataset_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def list_high_quality_datasets(self, min_quality: float = 0.8) -> List[Dict]:
        """List datasets meeting quality threshold."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM datasets 
                WHERE validation_status = 'VALIDATED' AND quality_score >= ?
                ORDER BY quality_score DESC
            """, (min_quality,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def load_dataset_for_analysis(self, dataset_id: int) -> Optional[LocomotionData]:
        """Load dataset for analysis."""
        info = self.get_dataset_info(dataset_id)
        if info and info['validation_status'] == 'VALIDATED':
            return LocomotionData(info['file_path'])
        return None

# Usage
db_manager = LocomotionDataManager('locomotion_studies.db')

# Register new dataset
dataset_id = db_manager.register_dataset('pilot_study', 'pilot_data_phase.parquet')

# List high-quality datasets
quality_datasets = db_manager.list_high_quality_datasets(min_quality=0.9)
for dataset in quality_datasets:
    print(f"{dataset['name']}: {dataset['quality_score']:.1%} quality")

# Load for analysis
loco = db_manager.load_dataset_for_analysis(dataset_id)
if loco:
    # Proceed with analysis
    pass
```

## Container Deployment

### Docker Integration

```dockerfile
# Dockerfile for locomotion data processing service
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY lib/ lib/
COPY docs/ docs/
COPY scripts/ scripts/

# Create data directories
RUN mkdir -p /data/input /data/output /data/reports

# Set environment variables
ENV PYTHONPATH=/app
ENV DATA_INPUT_DIR=/data/input
ENV DATA_OUTPUT_DIR=/data/output
ENV REPORTS_DIR=/data/reports

# Create non-root user
RUN useradd -m -u 1000 locomotion
USER locomotion

# Expose port for API
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "from lib.core.locomotion_analysis import LocomotionData; print('OK')" || exit 1

# Default command
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml for complete stack
version: '3.8'

services:
  locomotion-api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/data
      - ./config:/config
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/locomotion
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    restart: unless-stopped

  db:
    image: postgres:13
    environment:
      POSTGRES_DB: locomotion
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:6-alpine
    restart: unless-stopped

  worker:
    build: .
    command: celery worker -A api.tasks
    volumes:
      - ./data:/data
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/locomotion
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    restart: unless-stopped

volumes:
  postgres_data:
```

## Integration Best Practices

### Error Handling Strategy

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List

class ProcessingStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"

@dataclass
class ProcessingResult:
    status: ProcessingStatus
    message: str
    data: Optional[Dict] = None
    errors: Optional[List[str]] = None
    quality_score: Optional[float] = None

class RobustLocomotionProcessor:
    """Production-ready locomotion data processor with comprehensive error handling."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def process(self, dataset_path: str) -> ProcessingResult:
        """Process dataset with comprehensive error handling."""
        
        try:
            # Step 1: File validation
            if not Path(dataset_path).exists():
                return ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    message=f"Dataset file not found: {dataset_path}",
                    errors=["FILE_NOT_FOUND"]
                )
            
            # Step 2: Format validation
            try:
                validator = DatasetValidator(dataset_path, generate_plots=False)
                locomotion_data = validator.load_dataset()
                self.logger.info(f"Dataset loaded successfully: {dataset_path}")
            except ValueError as e:
                return ProcessingResult(
                    status=ProcessingStatus.REJECTED,
                    message=f"Invalid dataset format: {str(e)}",
                    errors=["INVALID_FORMAT"]
                )
            
            # Step 3: Quality validation
            try:
                validation_results = validator.validate_dataset(locomotion_data)
                quality_score = validation_results['valid_steps'] / validation_results['total_steps']
                
                if quality_score < self.config.get('min_quality_threshold', 0.7):
                    return ProcessingResult(
                        status=ProcessingStatus.REJECTED,
                        message=f"Dataset quality too low: {quality_score:.1%}",
                        errors=["LOW_QUALITY"],
                        quality_score=quality_score
                    )
                
                self.logger.info(f"Dataset validation passed: {quality_score:.1%} quality")
                
            except Exception as e:
                return ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    message=f"Validation failed: {str(e)}",
                    errors=["VALIDATION_ERROR"]
                )
            
            # Step 4: Feature extraction
            try:
                features = self._extract_features(locomotion_data)
                self.logger.info("Feature extraction completed")
            except Exception as e:
                return ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    message=f"Feature extraction failed: {str(e)}",
                    errors=["FEATURE_EXTRACTION_ERROR"]
                )
            
            # Success
            return ProcessingResult(
                status=ProcessingStatus.COMPLETED,
                message="Processing completed successfully",
                data={
                    'validation_results': validation_results,
                    'features': features,
                    'dataset_info': {
                        'subjects': len(locomotion_data.subjects),
                        'tasks': len(locomotion_data.tasks)
                    }
                },
                quality_score=quality_score
            )
            
        except Exception as e:
            self.logger.exception(f"Unexpected error processing {dataset_path}")
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                message=f"Unexpected error: {str(e)}",
                errors=["UNEXPECTED_ERROR"]
            )
    
    def _extract_features(self, locomotion_data: LocomotionData) -> Dict:
        """Extract features with error handling."""
        features = {}
        
        for subject in locomotion_data.subjects:
            subject_features = {}
            
            for task in locomotion_data.tasks:
                try:
                    data_3d, feature_names = locomotion_data.get_cycles(subject, task)
                    
                    if data_3d is not None and data_3d.shape[0] > 0:
                        # Calculate robust statistics
                        mean_patterns = np.mean(data_3d, axis=0)
                        rom_data = np.max(data_3d, axis=1) - np.min(data_3d, axis=1)
                        
                        subject_features[task] = {
                            'mean_patterns': mean_patterns.tolist(),
                            'mean_rom': np.mean(rom_data, axis=0).tolist(),
                            'cycle_count': data_3d.shape[0]
                        }
                        
                except Exception as e:
                    self.logger.warning(f"Could not extract features for {subject}-{task}: {e}")
                    continue
            
            if subject_features:  # Only add if we got some data
                features[subject] = subject_features
        
        return features

# Usage
config = {
    'min_quality_threshold': 0.8,
    'max_processing_time': 300  # 5 minutes
}

processor = RobustLocomotionProcessor(config)
result = processor.process('dataset_phase.parquet')

if result.status == ProcessingStatus.COMPLETED:
    print(f"Processing successful: {result.message}")
    print(f"Quality score: {result.quality_score:.1%}")
elif result.status == ProcessingStatus.REJECTED:
    print(f"Dataset rejected: {result.message}")
elif result.status == ProcessingStatus.FAILED:
    print(f"Processing failed: {result.message}")
    print(f"Errors: {result.errors}")
```

### Performance Monitoring

```python
import time
import psutil
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class PerformanceMetrics:
    processing_time: float
    memory_peak_mb: float
    cpu_percent: float
    dataset_size_mb: float
    subjects_count: int
    tasks_count: int
    throughput_subjects_per_second: float

class PerformanceMonitor:
    """Monitor performance of locomotion data processing."""
    
    def __init__(self):
        self.metrics_history: List[PerformanceMetrics] = []
    
    def monitor_processing(self, dataset_path: str, processor_func) -> PerformanceMetrics:
        """Monitor processing performance."""
        
        # Get dataset info
        dataset_size_mb = Path(dataset_path).stat().st_size / (1024 * 1024)
        
        # Start monitoring
        start_time = time.time()
        start_memory = psutil.virtual_memory().used / (1024 * 1024)
        process = psutil.Process()
        
        # Run processing
        result = processor_func(dataset_path)
        
        # Calculate metrics
        end_time = time.time()
        processing_time = end_time - start_time
        end_memory = psutil.virtual_memory().used / (1024 * 1024)
        memory_peak_mb = end_memory - start_memory
        cpu_percent = process.cpu_percent()
        
        # Get dataset characteristics
        subjects_count = len(result.get('subjects', []))
        tasks_count = len(result.get('tasks', []))
        throughput = subjects_count / processing_time if processing_time > 0 else 0
        
        metrics = PerformanceMetrics(
            processing_time=processing_time,
            memory_peak_mb=memory_peak_mb,
            cpu_percent=cpu_percent,
            dataset_size_mb=dataset_size_mb,
            subjects_count=subjects_count,
            tasks_count=tasks_count,
            throughput_subjects_per_second=throughput
        )
        
        self.metrics_history.append(metrics)
        return metrics
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary statistics."""
        if not self.metrics_history:
            return {}
        
        processing_times = [m.processing_time for m in self.metrics_history]
        memory_peaks = [m.memory_peak_mb for m in self.metrics_history]
        throughputs = [m.throughput_subjects_per_second for m in self.metrics_history]
        
        return {
            'total_datasets_processed': len(self.metrics_history),
            'avg_processing_time': np.mean(processing_times),
            'avg_memory_usage_mb': np.mean(memory_peaks),
            'avg_throughput_subjects_per_sec': np.mean(throughputs),
            'max_processing_time': np.max(processing_times),
            'max_memory_usage_mb': np.max(memory_peaks)
        }

# Usage
monitor = PerformanceMonitor()

def simple_processor(dataset_path):
    loco = LocomotionData(dataset_path)
    return {'subjects': loco.subjects, 'tasks': loco.tasks}

# Monitor processing
metrics = monitor.monitor_processing('dataset_phase.parquet', simple_processor)
print(f"Processing time: {metrics.processing_time:.2f}s")
print(f"Memory usage: {metrics.memory_peak_mb:.1f}MB")
print(f"Throughput: {metrics.throughput_subjects_per_second:.1f} subjects/sec")
```

## Next Steps

- **[ML Pipeline Integration](ml-pipeline-integration.md)** - Detailed ML workflow examples
- **[Performance Optimization](performance-optimization.md)** - Advanced optimization techniques
- **[Developer Workflows](../developer/README.md)** - Contributing and extending the platform