# Joint and Link Angle Conventions Diagram

This document provides visual representations of the joint and link angle conventions used in the locomotion data standardization framework.

## Coordinate System Reference

```plantuml
@startuml
!theme plain
skinparam backgroundColor white
skinparam defaultTextAlignment center

' Coordinate system
circle "Origin" as O #lightgray
O -right-> "+X\n(Anterior)" as X #red
O -up-> "+Y\n(Superior)" as Y #green  
O -down-> "+Z\n(Right)" as Z #blue

note right of X : Forward direction
note above of Y : Upward direction
note below of Z : Rightward direction

@enduml
```

**OpenSim Convention**: X = Anterior+, Y = Superior+, Z = Right+

## Sagittal Plane Joint Angles (Right Leg)

```plantuml
@startuml
!theme plain
skinparam backgroundColor white
skinparam defaultTextAlignment center
scale 1.2

' Define the anatomical chain with precise positioning
rectangle "Pelvis" as P #lightblue
circle "Hip Joint" as H #red
rectangle "Thigh" as T #lightgreen
circle "Knee Joint" as K #orange
rectangle "Shank" as S #lightcyan
circle "Ankle Joint" as A #purple
rectangle "Foot" as F #lightyellow

' Position elements vertically
P -down-> H : "Hip Flexion (+)\nThigh forward"
H -down-> T
T -down-> K : "Knee Flexion (+)\nHeel to buttocks"  
K -down-> S
S -down-> A : "Ankle Dorsiflexion (+)\nToes up"
A -down-> F

' Add angle indicators
note right of H
  **Hip Flexion (+)**
  Positive: Thigh moves forward
  Negative: Thigh moves backward
  Variable: hip_flexion_angle_*_rad
end note

note right of K
  **Knee Flexion (+)**
  Positive: Heel toward buttocks
  Negative: Leg straightens
  Variable: knee_flexion_angle_*_rad
end note

note right of A
  **Ankle Dorsiflexion (+)**
  Positive: Toes point up
  Negative: Toes point down (plantarflexion)
  Variable: ankle_dorsiflexion_angle_*_rad
end note

@enduml
```

## Link/Segment Angle Relationships

```plantuml
@startuml
!theme plain
skinparam backgroundColor white
skinparam defaultTextAlignment center

' Absolute segment orientations (left side)
package "Absolute Segment Orientations" as abs {
    rectangle "Pelvis Sagittal Angle\n(from global reference)" as PT #gold
    rectangle "Thigh Sagittal Angle\n= Pelvis Sagittal + Hip Flexion" as TA #lightcoral
    rectangle "Shank Sagittal Angle\n= Thigh Angle - Knee Flexion" as SA #lightgreen  
    rectangle "Foot Sagittal Angle\n= Shank Angle - Ankle Flexion" as FA #lightblue
}

' Joint angles (right side)
package "Joint Angles (Relative)" as rel {
    rectangle "Hip Flexion\n(Thigh relative to Pelvis)" as HF #pink
    rectangle "Knee Flexion\n(Shank relative to Thigh)" as KF #lightgreen
    rectangle "Ankle Dorsiflexion\n(Foot relative to Shank)" as AF #lightcyan
}

' Mathematical relationships
PT -down-> TA : "+"
HF -left-> TA : "+"
TA -down-> SA : "-"
KF -left-> SA : "-"
SA -down-> FA : "-"
AF -left-> FA : "-"

' Add calculation formulas
note bottom of TA : thigh_sagittal_angle = pelvis_sagittal + hip_flexion
note bottom of SA : shank_sagittal_angle = thigh_angle - knee_flexion
note bottom of FA : foot_sagittal_angle = shank_angle - ankle_flexion

@enduml
```

## Biomechanical Sign Conventions

### Joint Angles (Sagittal Plane)

| Joint | Positive Direction | Negative Direction | Variable Name |
|-------|-------------------|-------------------|---------------|
| **Hip** | Flexion (thigh forward) | Extension (thigh back) | `hip_flexion_angle_*_rad` |
| **Knee** | Flexion (heel to buttocks) | Extension (straight leg) | `knee_flexion_angle_*_rad` |
| **Ankle** | Dorsiflexion (toes up) | Plantarflexion (toes down) | `ankle_dorsiflexion_angle_*_rad` |

### Segment Angles (Absolute Orientations)

| Segment | Plane | Description | Variable Name |
|---------|-------|-------------|---------------|
| **Pelvis** | Sagittal | Anterior/posterior tilt | `pelvis_sagittal_angle_rad` |
| **Pelvis** | Frontal | Lateral tilt (obliquity) | `pelvis_frontal_angle_rad` |
| **Pelvis** | Transverse | Axial rotation | `pelvis_transverse_angle_rad` |
| **Trunk** | Sagittal | Forward/backward lean | `trunk_sagittal_angle_rad` |
| **Trunk** | Frontal | Lateral bend | `trunk_frontal_angle_rad` |
| **Trunk** | Transverse | Axial rotation | `trunk_transverse_angle_rad` |
| **Thigh** | Sagittal | Absolute thigh orientation | `thigh_sagittal_angle_*_rad` |
| **Shank** | Sagittal | Absolute shank orientation | `shank_sagittal_angle_*_rad` |
| **Foot** | Sagittal | Foot orientation | `foot_sagittal_angle_*_rad` |

**Note**: Segment angles use anatomical plane naming convention:
- **Sagittal plane**: Flexion/extension movements (forward/backward)
- **Frontal plane**: Abduction/adduction movements (side-to-side)
- **Transverse plane**: Rotation movements (for long bones, this is axial rotation)

## Multi-Plane Angle Conventions

```mermaid
graph LR
    subgraph "Sagittal Plane"
        S1["Hip Flexion (+)<br/>Knee Flexion (+)<br/>Ankle Dorsiflexion (+)"]
    end
    
    subgraph "Frontal Plane"
        F1["Hip Adduction (+)<br/>Knee Valgus (+)<br/>Ankle Eversion (+)"]
    end
    
    subgraph "Transverse Plane"
        T1["Hip External Rotation (+)<br/>Knee External Rotation (+)<br/>Ankle External Rotation (+)"]
    end
    
    style S1 fill:#ffcccc
    style F1 fill:#ccffcc
    style T1 fill:#ccccff
```

## Moment Sign Conventions

### Joint Moments (Net Internal Moments)

| Joint | Positive Moment | Biomechanical Meaning |
|-------|----------------|----------------------|
| **Hip** | Flexor moment | Hip flexors active |
| **Knee** | Extensor moment | Knee extensors active (typical in stance) |
| **Ankle** | Dorsiflexor moment | Dorsiflexors active |

**Note**: During walking, knee extensor moments are typically positive in stance phase to support body weight.

## Phase Relationships (Gait)

```mermaid
graph LR
    subgraph "Gait Cycle Phases"
        P0["0% - Initial Contact"]
        P25["25% - Loading Response"] 
        P50["50% - Mid Stance"]
        P75["75% - Terminal Stance"]
        P100["100% - Pre-swing"]
    end
    
    P0 --> P25 --> P50 --> P75 --> P100
    
    style P0 fill:#ffcccc
    style P25 fill:#ffddcc
    style P50 fill:#ffffcc
    style P75 fill:#ddffcc
    style P100 fill:#ccffcc
```

**Contralateral Offset**: Contralateral limb data is shifted by 50% of gait cycle (75 time points for 150-point cycles).

---

*These conventions align with OpenSim standards and biomechanical research practices.*