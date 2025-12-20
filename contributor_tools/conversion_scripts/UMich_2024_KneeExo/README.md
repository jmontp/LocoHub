# UMich 2024 Knee Exoskeleton Dataset

## Paper Information

**Title:** A Versatile Knee Exoskeleton Mitigates Quadriceps Fatigue in Lifting, Lowering, and Carrying Tasks

**Authors:** Nikhil V. Divekar, Gray C. Thomas, Avani R. Yerva, Hannah B. Frame, Robert D. Gregg

**Journal:** Science Robotics, Volume 9, Issue 94, September 2024

**DOI:** [10.1126/scirobotics.adr8282](https://doi.org/10.1126/scirobotics.adr8282)

**Data Repository:** [Dryad - doi:10.5061/dryad.z34tmpgks](https://doi.org/10.5061/dryad.z34tmpgks)

---

## Dataset Description

Data collected from 10 able-bodied participants performing fatiguing (S1) and non-fatiguing (S2) lifting-lowering-carrying (LLC) tasks with (exo condition) and without (bare condition) a bilateral knee exoskeleton. LLC tasks consist of squat lifting-lowering (LL), ramp ascent (RA), ramp descent (RD), stairs ascent (SA), stairs descent (SD), and level walking (LW). Ramp incline is 15 degrees and step height of stairs is 7 inches. dataset_S1 consists performance and posture measurements from fatiguing squat LL, and perceptual measurements from fatigued LLC tasks. dataset_S2 consists of electromyography, kinematics, torque, and foot sensor data from non-fatiguing LLC tasks.

### Tasks

| Code | Task | Description |
|------|------|-------------|
| LL | Squat Lift-Lower | Squat lifting and lowering movements |
| LW | Level Walking | Overground level walking |
| SA | Stair Ascent | Ascending stairs (7 inch step height) |
| SD | Stair Descent | Descending stairs (7 inch step height) |
| RA | Ramp Ascent | Walking up 15-degree incline |
| RD | Ramp Descent | Walking down 15-degree decline |

## Description of the Data and file structure

dataset_S1.mat contains 2 structures: 1) *emg* 2) *exo*.

1. *emg* is organized as emg.muscle.condition.task.measure, where the sub-structures are as follows. muscle: *quads, VMO, VL, RF, hams, ST, BF*; condition: *bare, exo*; task: *LL, LW, SA, SD, RA, RD*; measure: *ensemble, means*. ensemble is a 101 (0% to 100% task cycle) by 10 (subjects) array containing the time-normalized ensemble averaged emg profiles (normalized to %MVC). means is a 1 by 10 (subjects) array containing the means (in %MVC) of the emg profiles, i.e., the across cycle mean of ensemble. Note: quads contains the weighted (per physiological cross-sectional area) average emg data of vastus medialis oblique (VMO), rectus femoris (RF), and vastus lateralis (VL); and similarly hams contains un-weighted avearge emg data of biceps femoris (BF) and semitendinosus (ST).

2. *exo* is organized as exo.measure.task, where the sub-structures are as follows. measure: *torque, thighAngle, shankAngle, kneeAngle, grf;* task: *LL, LW, SA, SD, RA, RD*. Each task field is a 101 (0% to 100% task cycle) by 10 (subjects) array containing the corresponding ensemble averaged measures. Torque is in Nm (positive for extension); thighAngle is in degrees (positive for thigh anterior to vertical); shankAngle is in degrees (positive for shank anterior to vertical); kneeAngle is in degrees (positive for flexion); grf is the ground reaction force as measured by the foot sensor and is normalized to bodyweight.

dataset_S2.mat contains 11 structures:

1. *LLrepDuration_progression* contains two fields: *bare* and *exo*; each field contains 21 (-100% to 100% every 10%) by 10 (subjects) array containing the durations (in seconds) of the squat LL repetitions across % trial progression. The subjects declared fatigue at 0% trial progression. While a variable number of LL repetitions were performed pre-fatigue (-100% to 0% trial progression), a fixed set of 10 LL repetitions were performed post-fatigue (0% to 100% trial progression). Note that subjects were not allowed to pause in the pre-fatigue phase, but during the post-fatigue phase they could take the bare minimum pause between subsequent repetitions in order to maintain good squat posture.
2. *fatiguedCompletionTime_deficit* contains two fields: *bare* and *exo*; each field contains 1 by 10 (subjects) array containing the % increase in time to complete the 10 post-fatigue LL repetitions with respect to time required to complete the first 10 pre-fatigue LL repetitions in the bare condition.
3. *peakLean_progression* contains two fields: *bare* and *exo*; each field contains 21 (-100% to 100% every 10%) by 10 (subjects) array containing the peak sagittal thorax angles (in degrees, positive for trunk flexion) of the squat LL repetitions across % trial progression.
4. *fatiguedPeakLean* contains two fields: *bare* and *exo*; each field contains 1 by 10 (subjects) array containing the average peak sagittal thorax angle of the 10 post-fatigue LL repetitions.
5. *peakLean_deviation_progression* contains two fields: *bare* and *exo*; each field contains 21 (-100% to 100% every 10%) by 10 (subjects) array containing the deviation in peak sagittal thorax angles (in degrees) of the squat LL repetitions across % trial progression. Deviation is with respect to the minimum peak sagittal thorax angle observed in the pre-fatigue bare repetitions.
6. *fatiguedPeakLean_deviation* contains two fields: *bare* and *exo*; each field contains 1 by 10 (subjects) array containing the average deviation in peak sagittal thorax angle of the 10 post-fatigue LL repetitions.
7. *peakKneeFlexion_progression* contains two fields: *bare* and *exo*; each field contains 21 (-100% to 100% every 10%) by 10 (subjects) array containing the peak sagittal knee angles (in degrees, positive for flexion) of the squat LL repetitions across % trial progression.
8. *fatiguedPeakKneeFlexion* contains two fields: *bare* and *exo*; each field contains 1 by 10 (subjects) array containing the average peak sagittal knee angle of the 10 post-fatigue LL repetitions.
9. *peakKneeFlexion_deviation_progression* contains two fields: *bare* and *exo*; each field contains 21 (-100% to 100% every 10%) by 10 (subjects) array containing the deviation in peak sagittal knee angles (in degrees) of the squat LL repetitions across % trial progression. Deviation is with respect to the maximum peak sagittal knee angle observed in the pre-fatigue repetitions of the respective conditions.
10. *fatiguedPeakKneeFlexion_deviation* contains two fields: *bare* and *exo*; each field contains 1 by 10 (subjects) array containing the average deviation in peak sagittal knee angle of the 10 post-fatigue LL repetitions.
11. *modifiedquest* contains two fields: data and headers. data is a 6 (tasks) by 10 (subjects) array containing the modifiedQUEST ratings (out of 5) of the 6 tasks named in headers - a 6 (tasks) by 1 string array.

## Sharing/access Information

There are no other publicly accessible locations of the data.

Data was not derived from any other source.

---

## Conversion Notes

The conversion script (`convert_umich_2024_phase_to_parquet.py`) processes `dataset_S1.mat`:

1. Resamples from 101 to 150 points per cycle
2. Converts angles from degrees to radians
3. Inverts torque sign (extension positive → flexion positive)
4. Maps tasks to standardized names:
   - LL → squat
   - LW → level_walking
   - SA → stair_ascent
   - SD → stair_descent
   - RA → incline_walking (15 deg)
   - RD → decline_walking (15 deg)

### Available Features

| Feature | Available | Notes |
|---------|-----------|-------|
| Knee angle | ✅ | Flexion positive |
| Hip angle | ❌ | Not in source data |
| Ankle angle | ❌ | Not in source data |
| Thigh segment angle | ✅ | Anterior to vertical |
| Shank segment angle | ✅ | Anterior to vertical |
| GRF (vertical) | ✅ | Body-weight normalized |
| Exo torque | ✅ | Custom column (Nm) |
| EMG | ❌ | Available in source but not converted |

### Running the Conversion

```bash
cd contributor_tools/conversion_scripts/UMich_2024_KneeExo
python3 convert_umich_2024_phase_to_parquet.py
```

Output: `converted_datasets/umich_2024_knee_exo_phase.parquet`

## Citation

If using this dataset, please cite:

```bibtex
@article{divekar2024versatile,
  title={A versatile knee exoskeleton mitigates quadriceps fatigue in lifting, lowering, and carrying tasks},
  author={Divekar, Nikhil V and Thomas, Gray C and Yerva, Avani R and Frame, Hannah B and Gregg, Robert D},
  journal={Science Robotics},
  volume={9},
  number={94},
  pages={eadr8282},
  year={2024},
  publisher={American Association for the Advancement of Science},
  doi={10.1126/scirobotics.adr8282}
}
```
