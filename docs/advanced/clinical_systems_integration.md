# Clinical Systems Integration Guide

**Complete guide for integrating locomotion data with clinical systems and workflows**

## Overview

This guide demonstrates how to integrate the locomotion data platform with clinical systems, electronic health records (EHR), DICOM infrastructure, and clinical decision support tools for biomechanical assessment and patient care.

## Clinical Data Standards Integration

### HL7 FHIR Integration

```python
from lib.core.locomotion_analysis import LocomotionData
import json
from datetime import datetime, timezone
import uuid

class HL7FHIRGaitExporter:
    """Export gait analysis results to HL7 FHIR format."""
    
    def __init__(self, loco_data):
        self.loco_data = loco_data
        
    def create_patient_resource(self, patient_id, name=None, birth_date=None, gender=None):
        """Create FHIR Patient resource."""
        
        patient = {
            "resourceType": "Patient",
            "id": patient_id,
            "identifier": [{
                "use": "official",
                "system": "http://hospital.smartplatforms.org",
                "value": patient_id
            }]
        }
        
        if name:
            patient["name"] = [{
                "use": "official",
                "family": name.get("family", ""),
                "given": name.get("given", [])
            }]
        
        if birth_date:
            patient["birthDate"] = birth_date
            
        if gender:
            patient["gender"] = gender
            
        return patient
    
    def create_observation_resource(self, patient_id, subject, task, measurement_type="gait_analysis"):
        """Create FHIR Observation resource for gait measurements."""
        
        # Get gait analysis results
        summary_stats = self.loco_data.get_summary_statistics(subject, task)
        rom_data = self.loco_data.calculate_rom(subject, task, by_cycle=False)
        
        observation = {
            "resourceType": "Observation",
            "id": str(uuid.uuid4()),
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "survey",
                    "display": "Survey"
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "72133-2",
                    "display": "Gait analysis"
                }]
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "effectiveDateTime": datetime.now(timezone.utc).isoformat(),
            "component": []
        }
        
        # Add ROM measurements as components
        for feature, rom_value in rom_data.items():
            if 'angle' in feature:  # Only include angle measurements
                joint = feature.split('_')[0]
                side = 'left' if 'contra' in feature else 'right'
                
                component = {
                    "code": {
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "364564000",
                            "display": f"{joint.title()} range of motion"
                        }],
                        "text": f"{joint.title()} {side} ROM - {task}"
                    },
                    "valueQuantity": {
                        "value": float(np.degrees(rom_value)),  # Convert to degrees
                        "unit": "degrees",
                        "system": "http://unitsofmeasure.org",
                        "code": "deg"
                    }
                }
                observation["component"].append(component)
        
        return observation
    
    def create_diagnostic_report(self, patient_id, subject, tasks, performer=None):
        """Create FHIR DiagnosticReport for comprehensive gait analysis."""
        
        report = {
            "resourceType": "DiagnosticReport",
            "id": str(uuid.uuid4()),
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                    "code": "PHY",
                    "display": "Physician (Psychiatrist)"
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "72133-2",
                    "display": "Gait analysis study"
                }]
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "effectiveDateTime": datetime.now(timezone.utc).isoformat(),
            "issued": datetime.now(timezone.utc).isoformat(),
            "result": [],
            "conclusion": ""
        }
        
        if performer:
            report["performer"] = [{
                "reference": f"Practitioner/{performer}"
            }]
        
        # Create observations for each task
        conclusions = []
        for task in tasks:
            try:
                observation = self.create_observation_resource(patient_id, subject, task)
                report["result"].append({
                    "reference": f"Observation/{observation['id']}"
                })
                
                # Generate clinical interpretation
                interpretation = self.generate_clinical_interpretation(subject, task)
                conclusions.append(f"{task.replace('_', ' ').title()}: {interpretation}")
                
            except Exception as e:
                print(f"Error processing task {task}: {e}")
        
        report["conclusion"] = "; ".join(conclusions)
        
        return report
    
    def generate_clinical_interpretation(self, subject, task):
        """Generate clinical interpretation of gait analysis."""
        
        try:
            # Get analysis results
            rom_data = self.loco_data.calculate_rom(subject, task, by_cycle=False)
            valid_cycles = self.loco_data.validate_cycles(subject, task)
            
            interpretations = []
            
            # Data quality assessment
            if len(valid_cycles) > 0:
                quality_percentage = (valid_cycles.sum() / len(valid_cycles)) * 100
                if quality_percentage < 70:
                    interpretations.append("Poor data quality detected")
                elif quality_percentage > 90:
                    interpretations.append("High quality gait data")
            
            # ROM assessment
            for feature, rom_value in rom_data.items():
                if 'knee_flexion_angle' in feature:
                    rom_degrees = np.degrees(rom_value)
                    if rom_degrees < 45:
                        interpretations.append("Reduced knee flexion ROM")
                    elif rom_degrees > 75:
                        interpretations.append("Excessive knee flexion ROM")
                    else:
                        interpretations.append("Normal knee flexion ROM")
                    break
            
            return "; ".join(interpretations) if interpretations else "Normal gait pattern"
            
        except Exception as e:
            return f"Analysis incomplete: {str(e)}"
    
    def export_patient_bundle(self, patient_id, subject, tasks, patient_info=None, output_path=None):
        """Export complete patient data as FHIR Bundle."""
        
        bundle = {
            "resourceType": "Bundle",
            "id": str(uuid.uuid4()),
            "type": "document",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "entry": []
        }
        
        # Add patient resource
        patient_resource = self.create_patient_resource(patient_id, **patient_info or {})
        bundle["entry"].append({
            "resource": patient_resource
        })
        
        # Add diagnostic report
        diagnostic_report = self.create_diagnostic_report(patient_id, subject, tasks)
        bundle["entry"].append({
            "resource": diagnostic_report
        })
        
        # Add individual observations
        for task in tasks:
            try:
                observation = self.create_observation_resource(patient_id, subject, task)
                bundle["entry"].append({
                    "resource": observation
                })
            except Exception as e:
                print(f"Error creating observation for {task}: {e}")
        
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(bundle, f, indent=2)
            print(f"FHIR bundle exported to {output_path}")
        
        return bundle

# Usage example
loco = LocomotionData('clinical_dataset_phase.parquet')
fhir_exporter = HL7FHIRGaitExporter(loco)

# Export patient data
patient_info = {
    "name": {"family": "Smith", "given": ["John"]},
    "birth_date": "1980-01-15",
    "gender": "male"
}

bundle = fhir_exporter.export_patient_bundle(
    patient_id="PATIENT_001",
    subject="SUB01", 
    tasks=['normal_walk', 'fast_walk'],
    patient_info=patient_info,
    output_path="patient_001_gait_analysis.json"
)
```

### DICOM Integration

```python
import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import generate_uid
import numpy as np
import matplotlib.pyplot as plt
import io

class DICOMGaitExporter:
    """Export gait analysis results to DICOM format."""
    
    def __init__(self, loco_data):
        self.loco_data = loco_data
        
    def create_dicom_waveform(self, subject, task, features=None, output_path=None):
        """Create DICOM waveform object for gait data."""
        
        # Get gait cycle data
        data_3d, feature_names = self.loco_data.get_cycles(subject, task, features)
        if data_3d is None:
            raise ValueError(f"No data found for {subject}-{task}")
        
        # Create mean gait cycle
        mean_cycle = np.mean(data_3d, axis=0)  # Shape: (150, n_features)
        
        # Create DICOM dataset
        ds = Dataset()
        
        # DICOM metadata
        ds.PatientID = subject
        ds.PatientName = subject
        ds.StudyDescription = f"Gait Analysis - {task}"
        ds.SeriesDescription = "Biomechanical Waveform"
        ds.Modality = "OP"  # Other
        ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.9.1.1"  # Waveform Storage
        ds.SOPInstanceUID = generate_uid()
        ds.StudyInstanceUID = generate_uid()
        ds.SeriesInstanceUID = generate_uid()
        
        # Waveform data
        ds.SamplingFrequency = 150  # 150 samples per gait cycle
        ds.NumberOfWaveformChannels = len(feature_names)
        ds.NumberOfWaveformSamples = 150
        
        # Convert to appropriate format (16-bit signed integer)
        waveform_data = (mean_cycle * 1000).astype(np.int16)  # Scale for precision
        ds.WaveformData = waveform_data.tobytes()
        
        # Channel definitions
        channel_definitions = []
        for i, feature in enumerate(feature_names):
            channel_def = Dataset()
            channel_def.ChannelLabel = feature[:16]  # DICOM limit
            channel_def.ChannelStatus = "OK"
            channel_def.ChannelSourceSequence = [Dataset()]
            channel_def.ChannelSensitivity = 0.001  # Scale factor
            channel_def.ChannelSensitivityUnitsSequence = [Dataset()]
            channel_definitions.append(channel_def)
        
        ds.ChannelDefinitionSequence = channel_definitions
        
        if output_path:
            ds.save_as(output_path)
            print(f"DICOM waveform saved to {output_path}")
        
        return ds
    
    def create_dicom_image(self, subject, task, features=None, output_path=None):
        """Create DICOM image from gait visualization."""
        
        # Generate gait pattern plot
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Plot gait patterns
        data_3d, feature_names = self.loco_data.get_cycles(subject, task, features)
        if data_3d is None:
            raise ValueError(f"No data found for {subject}-{task}")
        
        phase_x = np.linspace(0, 100, 150)
        
        for i, feature in enumerate(feature_names):
            mean_pattern = np.mean(data_3d[:, :, i], axis=0)
            ax.plot(phase_x, mean_pattern, label=feature.replace('_', ' '))
        
        ax.set_xlabel('Gait Cycle (%)')
        ax.set_ylabel('Joint Angle (rad)')
        ax.set_title(f'Gait Analysis - {subject} - {task}')
        ax.legend()
        ax.grid(True)
        
        # Convert plot to image array
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        
        # Read image as array
        from PIL import Image
        image = Image.open(buf)
        image_array = np.array(image)
        plt.close()
        
        # Create DICOM dataset
        ds = Dataset()
        
        # DICOM metadata
        ds.PatientID = subject
        ds.PatientName = subject
        ds.StudyDescription = f"Gait Analysis - {task}"
        ds.SeriesDescription = "Gait Pattern Visualization"
        ds.Modality = "OT"  # Other
        ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.7"  # Secondary Capture Image
        ds.SOPInstanceUID = generate_uid()
        ds.StudyInstanceUID = generate_uid()
        ds.SeriesInstanceUID = generate_uid()
        
        # Image data
        if len(image_array.shape) == 3:  # RGB
            ds.SamplesPerPixel = 3
            ds.PhotometricInterpretation = "RGB"
            ds.PlanarConfiguration = 0
            pixel_data = image_array
        else:  # Grayscale
            ds.SamplesPerPixel = 1
            ds.PhotometricInterpretation = "MONOCHROME2"
            pixel_data = image_array
        
        ds.Rows = pixel_data.shape[0]
        ds.Columns = pixel_data.shape[1]
        ds.BitsAllocated = 8
        ds.BitsStored = 8
        ds.HighBit = 7
        ds.PixelRepresentation = 0
        
        ds.PixelData = pixel_data.tobytes()
        
        if output_path:
            ds.save_as(output_path)
            print(f"DICOM image saved to {output_path}")
        
        return ds

# Usage
loco = LocomotionData('clinical_dataset_phase.parquet')
dicom_exporter = DICOMGaitExporter(loco)

# Create DICOM waveform
dicom_waveform = dicom_exporter.create_dicom_waveform(
    'SUB01', 'normal_walk', 
    features=['knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad'],
    output_path='gait_waveform.dcm'
)

# Create DICOM image
dicom_image = dicom_exporter.create_dicom_image(
    'SUB01', 'normal_walk',
    output_path='gait_visualization.dcm'
)
```

## Electronic Health Record Integration

### Epic EHR Integration

```python
import requests
import base64
from typing import Dict, List

class EpicEHRIntegration:
    """Integration with Epic EHR systems via FHIR API."""
    
    def __init__(self, base_url, client_id, client_secret):
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        
    def authenticate(self):
        """Authenticate with Epic EHR system."""
        
        auth_url = f"{self.base_url}/oauth2/token"
        
        # Create authorization header
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'client_credentials',
            'scope': 'patient/*.read observation/*.write diagnosticreport/*.write'
        }
        
        response = requests.post(auth_url, headers=headers, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data['access_token']
            print("Successfully authenticated with Epic EHR")
        else:
            raise Exception(f"Authentication failed: {response.text}")
    
    def search_patient(self, patient_identifier):
        """Search for patient in Epic EHR."""
        
        if not self.access_token:
            self.authenticate()
        
        search_url = f"{self.base_url}/Patient"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/fhir+json'
        }
        
        params = {
            'identifier': patient_identifier
        }
        
        response = requests.get(search_url, headers=headers, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Patient search failed: {response.text}")
    
    def create_gait_observation(self, patient_id, gait_data):
        """Create gait analysis observation in Epic EHR."""
        
        if not self.access_token:
            self.authenticate()
        
        observation_url = f"{self.base_url}/Observation"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/fhir+json',
            'Accept': 'application/fhir+json'
        }
        
        response = requests.post(observation_url, headers=headers, json=gait_data)
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            raise Exception(f"Observation creation failed: {response.text}")
    
    def submit_gait_analysis(self, patient_identifier, subject, task, loco_data):
        """Complete workflow to submit gait analysis to Epic EHR."""
        
        try:
            # Search for patient
            patient_search = self.search_patient(patient_identifier)
            if patient_search['total'] == 0:
                raise Exception("Patient not found in EHR")
            
            patient_id = patient_search['entry'][0]['resource']['id']
            
            # Create gait observation using FHIR exporter
            fhir_exporter = HL7FHIRGaitExporter(loco_data)
            observation = fhir_exporter.create_observation_resource(patient_id, subject, task)
            
            # Submit to Epic
            result = self.create_gait_observation(patient_id, observation)
            
            print(f"Gait analysis successfully submitted to Epic EHR")
            print(f"Observation ID: {result.get('id', 'Unknown')}")
            
            return result
            
        except Exception as e:
            print(f"Error submitting gait analysis: {e}")
            raise

# Usage (with proper credentials)
"""
epic_integration = EpicEHRIntegration(
    base_url="https://fhir.epic.com/interconnect-fhir-oauth",
    client_id="your_client_id",
    client_secret="your_client_secret"
)

# Submit gait analysis to Epic EHR
loco = LocomotionData('clinical_dataset_phase.parquet')
epic_integration.submit_gait_analysis("MRN123456", "SUB01", "normal_walk", loco)
"""
```

### Cerner Integration

```python
class CernerIntegration:
    """Integration with Cerner EHR systems."""
    
    def __init__(self, base_url, client_id, client_secret):
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
    
    def authenticate(self):
        """Authenticate with Cerner system."""
        
        auth_url = f"{self.base_url}/realms/d075cf2f-b4e8-4b40-b8c7-c8c6b6cb0e48/protocol/openid-connect/token"
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'system/Patient.read system/Observation.write'
        }
        
        response = requests.post(auth_url, headers=headers, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data['access_token']
            print("Successfully authenticated with Cerner")
        else:
            raise Exception(f"Cerner authentication failed: {response.text}")
    
    def create_structured_gait_report(self, patient_id, subject, task, loco_data):
        """Create structured gait analysis report for Cerner."""
        
        # Get comprehensive gait analysis
        summary_stats = loco_data.get_summary_statistics(subject, task)
        rom_data = loco_data.calculate_rom(subject, task, by_cycle=False)
        valid_cycles = loco_data.validate_cycles(subject, task)
        
        # Create structured report
        report = {
            "resourceType": "DiagnosticReport",
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                    "code": "PHY",
                    "display": "Physical Therapy"
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "72133-2",
                    "display": "Gait analysis study"
                }]
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "effectiveDateTime": datetime.now(timezone.utc).isoformat(),
            "presentedForm": [{
                "contentType": "text/html",
                "data": base64.b64encode(self.generate_html_report(
                    subject, task, summary_stats, rom_data, valid_cycles
                ).encode()).decode()
            }]
        }
        
        return report
    
    def generate_html_report(self, subject, task, summary_stats, rom_data, valid_cycles):
        """Generate HTML report for clinical review."""
        
        quality_percentage = (valid_cycles.sum() / len(valid_cycles)) * 100 if len(valid_cycles) > 0 else 0
        
        html = f"""
        <html>
        <head><title>Gait Analysis Report</title></head>
        <body>
        <h2>Gait Analysis Report</h2>
        <h3>Patient: {subject}</h3>
        <h3>Task: {task.replace('_', ' ').title()}</h3>
        <h3>Date: {datetime.now().strftime('%Y-%m-%d')}</h3>
        
        <h4>Data Quality</h4>
        <p>Valid gait cycles: {valid_cycles.sum()}/{len(valid_cycles)} ({quality_percentage:.1f}%)</p>
        
        <h4>Range of Motion Analysis</h4>
        <table border="1">
        <tr><th>Joint</th><th>ROM (degrees)</th><th>Clinical Interpretation</th></tr>
        """
        
        for feature, rom_value in rom_data.items():
            if 'angle' in feature:
                joint = feature.split('_')[0]
                rom_degrees = np.degrees(rom_value)
                
                # Clinical interpretation
                if 'knee' in feature:
                    if rom_degrees < 45:
                        interpretation = "Reduced ROM - Consider intervention"
                    elif rom_degrees > 75:
                        interpretation = "Excessive ROM - Monitor for instability"
                    else:
                        interpretation = "Normal ROM"
                elif 'hip' in feature:
                    if rom_degrees < 25:
                        interpretation = "Reduced ROM - May affect stride length"
                    elif rom_degrees > 50:
                        interpretation = "Excessive ROM - Monitor for compensation"
                    else:
                        interpretation = "Normal ROM"
                elif 'ankle' in feature:
                    if rom_degrees < 15:
                        interpretation = "Reduced ROM - May affect push-off"
                    elif rom_degrees > 35:
                        interpretation = "Excessive ROM - Monitor for foot drop"
                    else:
                        interpretation = "Normal ROM"
                else:
                    interpretation = "Within expected range"
                
                html += f"""
                <tr>
                <td>{joint.title()}</td>
                <td>{rom_degrees:.1f}</td>
                <td>{interpretation}</td>
                </tr>
                """
        
        html += """
        </table>
        
        <h4>Clinical Recommendations</h4>
        <ul>
        """
        
        # Generate recommendations based on findings
        recommendations = []
        
        if quality_percentage < 70:
            recommendations.append("Repeat assessment due to poor data quality")
        
        for feature, rom_value in rom_data.items():
            if 'knee_flexion_angle' in feature:
                rom_degrees = np.degrees(rom_value)
                if rom_degrees < 45:
                    recommendations.append("Consider knee flexion exercises and stretching")
                elif rom_degrees > 75:
                    recommendations.append("Evaluate for knee instability or weakness")
        
        if not recommendations:
            recommendations.append("Continue current treatment plan")
            recommendations.append("Follow up in 3 months")
        
        for rec in recommendations:
            html += f"<li>{rec}</li>"
        
        html += """
        </ul>
        </body>
        </html>
        """
        
        return html

# Usage
"""
cerner_integration = CernerIntegration(
    base_url="https://fhir-open.cerner.com",
    client_id="your_client_id", 
    client_secret="your_client_secret"
)

loco = LocomotionData('clinical_dataset_phase.parquet')
report = cerner_integration.create_structured_gait_report("12345", "SUB01", "normal_walk", loco)
"""
```

## Clinical Decision Support

### Risk Assessment Pipeline

```python
class ClinicalRiskAssessment:
    """Clinical risk assessment based on gait analysis."""
    
    def __init__(self, loco_data):
        self.loco_data = loco_data
        
    def assess_fall_risk(self, subject, task='normal_walk'):
        """Assess fall risk based on gait parameters."""
        
        try:
            # Get gait data
            data_3d, features = self.loco_data.get_cycles(subject, task)
            if data_3d is None:
                return {"error": "No gait data available"}
            
            # Calculate variability metrics
            cv_variability = self.calculate_coefficient_variation(data_3d)
            rom_data = self.loco_data.calculate_rom(subject, task, by_cycle=False)
            
            # Fall risk factors
            risk_factors = []
            risk_score = 0
            
            # 1. Gait variability (high variability = increased fall risk)
            if cv_variability > 0.15:  # High variability threshold
                risk_factors.append("High gait variability detected")
                risk_score += 2
            elif cv_variability > 0.10:
                risk_factors.append("Moderate gait variability")
                risk_score += 1
            
            # 2. Range of motion deficits
            for feature, rom_value in rom_data.items():
                if 'knee_flexion_angle' in feature:
                    rom_degrees = np.degrees(rom_value)
                    if rom_degrees < 45:
                        risk_factors.append("Reduced knee flexion ROM")
                        risk_score += 1
                elif 'ankle_flexion_angle' in feature:
                    rom_degrees = np.degrees(rom_value)
                    if rom_degrees < 15:
                        risk_factors.append("Reduced ankle flexion ROM")
                        risk_score += 1
            
            # 3. Asymmetry assessment
            asymmetry_score = self.assess_gait_asymmetry(data_3d, features)
            if asymmetry_score > 0.2:
                risk_factors.append("Significant gait asymmetry")
                risk_score += 2
            elif asymmetry_score > 0.1:
                risk_factors.append("Mild gait asymmetry")
                risk_score += 1
            
            # Determine risk level
            if risk_score >= 4:
                risk_level = "High"
                recommendations = [
                    "Immediate fall prevention intervention recommended",
                    "Consider physical therapy evaluation",
                    "Home safety assessment advised"
                ]
            elif risk_score >= 2:
                risk_level = "Moderate"
                recommendations = [
                    "Fall prevention education recommended",
                    "Regular monitoring advised",
                    "Consider balance training"
                ]
            else:
                risk_level = "Low"
                recommendations = [
                    "Continue current activity level",
                    "Routine follow-up in 6 months"
                ]
            
            return {
                "risk_level": risk_level,
                "risk_score": risk_score,
                "risk_factors": risk_factors,
                "recommendations": recommendations,
                "metrics": {
                    "gait_variability": cv_variability,
                    "asymmetry_score": asymmetry_score,
                    "rom_data": {k: np.degrees(v) for k, v in rom_data.items()}
                }
            }
            
        except Exception as e:
            return {"error": f"Risk assessment failed: {str(e)}"}
    
    def calculate_coefficient_variation(self, data_3d):
        """Calculate coefficient of variation across gait cycles."""
        
        # Calculate CV for each feature and take mean
        cvs = []
        for feature_idx in range(data_3d.shape[2]):
            feature_data = data_3d[:, :, feature_idx]
            means = np.mean(feature_data, axis=1)  # Mean per cycle
            std_devs = np.std(feature_data, axis=1)  # Std per cycle
            
            # Calculate CV (avoid division by zero)
            cv = np.divide(std_devs, means, out=np.zeros_like(std_devs), where=means!=0)
            cvs.append(np.mean(cv))
        
        return np.mean(cvs)
    
    def assess_gait_asymmetry(self, data_3d, features):
        """Assess asymmetry between left and right limbs."""
        
        asymmetry_scores = []
        
        for i, feature in enumerate(features):
            if 'ipsi' in feature:
                # Find corresponding contralateral feature
                contra_feature = feature.replace('ipsi', 'contra')
                if contra_feature in features:
                    j = features.index(contra_feature)
                    
                    # Calculate asymmetry as normalized difference
                    ipsi_data = data_3d[:, :, i]
                    contra_data = data_3d[:, :, j]
                    
                    # Mean patterns
                    ipsi_mean = np.mean(ipsi_data, axis=0)
                    contra_mean = np.mean(contra_data, axis=0)
                    
                    # Calculate asymmetry index
                    asymmetry = np.abs(ipsi_mean - contra_mean) / (np.abs(ipsi_mean) + np.abs(contra_mean) + 1e-8)
                    asymmetry_scores.append(np.mean(asymmetry))
        
        return np.mean(asymmetry_scores) if asymmetry_scores else 0
    
    def generate_clinical_alert(self, subject, risk_assessment):
        """Generate clinical alert if high risk detected."""
        
        if risk_assessment.get("risk_level") == "High":
            alert = {
                "alert_type": "FALL_RISK_HIGH",
                "patient_id": subject,
                "severity": "HIGH",
                "message": f"High fall risk detected for patient {subject}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": risk_assessment,
                "actions_required": [
                    "Schedule immediate fall prevention consultation",
                    "Notify primary care physician",
                    "Initiate safety precautions"
                ]
            }
            
            return alert
        
        return None

# Usage
loco = LocomotionData('clinical_dataset_phase.parquet')
risk_assessor = ClinicalRiskAssessment(loco)

# Assess fall risk
risk_result = risk_assessor.assess_fall_risk('SUB01', 'normal_walk')
print(f"Fall Risk Assessment:")
print(f"Risk Level: {risk_result['risk_level']}")
print(f"Risk Score: {risk_result['risk_score']}")
print(f"Risk Factors: {risk_result['risk_factors']}")

# Generate alert if needed
alert = risk_assessor.generate_clinical_alert('SUB01', risk_result)
if alert:
    print(f"CLINICAL ALERT: {alert['message']}")
```

## Outcome Tracking and Reporting

### Longitudinal Analysis

```python
class LongitudinalGaitAnalysis:
    """Track gait changes over time for clinical outcomes."""
    
    def __init__(self):
        self.patient_data = {}
        
    def add_assessment(self, patient_id, assessment_date, loco_data, subject, task):
        """Add gait assessment for longitudinal tracking."""
        
        if patient_id not in self.patient_data:
            self.patient_data[patient_id] = []
        
        # Extract key metrics
        summary_stats = loco_data.get_summary_statistics(subject, task)
        rom_data = loco_data.calculate_rom(subject, task, by_cycle=False)
        valid_cycles = loco_data.validate_cycles(subject, task)
        
        assessment = {
            "date": assessment_date,
            "subject": subject,
            "task": task,
            "data_quality": valid_cycles.sum() / len(valid_cycles) if len(valid_cycles) > 0 else 0,
            "rom_metrics": {k: np.degrees(v) for k, v in rom_data.items()},
            "summary_stats": summary_stats.to_dict() if not summary_stats.empty else {}
        }
        
        self.patient_data[patient_id].append(assessment)
        self.patient_data[patient_id].sort(key=lambda x: x["date"])
    
    def analyze_progression(self, patient_id, metric="knee_flexion_angle_ipsi_rad"):
        """Analyze progression of specific metric over time."""
        
        if patient_id not in self.patient_data:
            return {"error": "Patient not found"}
        
        assessments = self.patient_data[patient_id]
        if len(assessments) < 2:
            return {"error": "Insufficient assessments for progression analysis"}
        
        # Extract metric values over time
        dates = [a["date"] for a in assessments]
        values = []
        
        for assessment in assessments:
            if metric in assessment["rom_metrics"]:
                values.append(assessment["rom_metrics"][metric])
            elif metric in assessment["summary_stats"]:
                values.append(assessment["summary_stats"][metric]["mean"])
            else:
                values.append(None)
        
        # Calculate progression
        valid_values = [(d, v) for d, v in zip(dates, values) if v is not None]
        
        if len(valid_values) < 2:
            return {"error": f"Insufficient data for metric {metric}"}
        
        # Calculate trend
        from scipy import stats
        x_numeric = [i for i in range(len(valid_values))]
        y_values = [v[1] for v in valid_values]
        
        slope, intercept, r_value, p_value, std_err = stats.linregress(x_numeric, y_values)
        
        # Determine clinical significance
        if abs(slope) < 0.1:
            trend = "Stable"
        elif slope > 0:
            trend = "Improving"
        else:
            trend = "Declining"
        
        # Calculate effect size
        baseline_value = y_values[0]
        latest_value = y_values[-1]
        percent_change = ((latest_value - baseline_value) / baseline_value) * 100
        
        return {
            "metric": metric,
            "trend": trend,
            "slope": slope,
            "r_squared": r_value**2,
            "p_value": p_value,
            "baseline_value": baseline_value,
            "latest_value": latest_value,
            "percent_change": percent_change,
            "assessments": valid_values,
            "clinical_significance": "Significant" if abs(percent_change) > 10 else "Minimal"
        }
    
    def generate_progress_report(self, patient_id, output_path=None):
        """Generate comprehensive progress report."""
        
        if patient_id not in self.patient_data:
            return {"error": "Patient not found"}
        
        assessments = self.patient_data[patient_id]
        
        # Key metrics to track
        key_metrics = [
            "knee_flexion_angle_ipsi_rad",
            "hip_flexion_angle_ipsi_rad",
            "ankle_flexion_angle_ipsi_rad"
        ]
        
        report = {
            "patient_id": patient_id,
            "assessment_period": {
                "start_date": assessments[0]["date"],
                "end_date": assessments[-1]["date"],
                "total_assessments": len(assessments)
            },
            "metric_progressions": {},
            "overall_trend": "",
            "clinical_recommendations": []
        }
        
        # Analyze each metric
        improving_metrics = 0
        declining_metrics = 0
        
        for metric in key_metrics:
            progression = self.analyze_progression(patient_id, metric)
            if "error" not in progression:
                report["metric_progressions"][metric] = progression
                
                if progression["trend"] == "Improving":
                    improving_metrics += 1
                elif progression["trend"] == "Declining":
                    declining_metrics += 1
        
        # Overall assessment
        if improving_metrics > declining_metrics:
            report["overall_trend"] = "Improving"
            report["clinical_recommendations"].append("Continue current treatment plan")
        elif declining_metrics > improving_metrics:
            report["overall_trend"] = "Declining"
            report["clinical_recommendations"].append("Consider treatment plan modification")
            report["clinical_recommendations"].append("Schedule additional assessments")
        else:
            report["overall_trend"] = "Stable"
            report["clinical_recommendations"].append("Maintain current interventions")
        
        # Data quality assessment
        avg_quality = np.mean([a["data_quality"] for a in assessments])
        if avg_quality < 0.8:
            report["clinical_recommendations"].append("Improve data collection quality")
        
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"Progress report saved to {output_path}")
        
        return report

# Usage
longitudinal_analyzer = LongitudinalGaitAnalysis()

# Add multiple assessments
loco1 = LocomotionData('baseline_assessment_phase.parquet')
loco2 = LocomotionData('followup_3month_phase.parquet')
loco3 = LocomotionData('followup_6month_phase.parquet')

longitudinal_analyzer.add_assessment("PATIENT_001", "2024-01-15", loco1, "SUB01", "normal_walk")
longitudinal_analyzer.add_assessment("PATIENT_001", "2024-04-15", loco2, "SUB01", "normal_walk")
longitudinal_analyzer.add_assessment("PATIENT_001", "2024-07-15", loco3, "SUB01", "normal_walk")

# Analyze progression
progression = longitudinal_analyzer.analyze_progression("PATIENT_001", "knee_flexion_angle_ipsi_rad")
print(f"Knee ROM progression: {progression['trend']} ({progression['percent_change']:.1f}% change)")

# Generate progress report
progress_report = longitudinal_analyzer.generate_progress_report("PATIENT_001", "patient_001_progress.json")
print(f"Overall trend: {progress_report['overall_trend']}")
```

This comprehensive clinical systems integration guide provides complete patterns for integrating the locomotion data platform with clinical workflows, EHR systems, and decision support tools.