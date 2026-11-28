---
title: Read and inspect data
---

# Read and inspect data

Use native file readers to inspect observations and create a first plot. No LocoHub analysis package is needed.

## Download the example

[Download CSV](assets/locohub_example_data.csv){ .md-button .md-button--primary download="locohub_example_data.csv" }
[Download Parquet](assets/locohub_example_data.parquet){ .md-button download="locohub_example_data.parquet" }

Both files contain **600 rows: four complete observations, two synthetic subjects, 150 points per observation**. The phase grid includes 0 and 100%. Values are artificial and exist only to demonstrate the file format and analysis steps; they are not participant measurements, a released research dataset, or evidence for biomechanical ranges.

Save both files in your working directory. The examples below use the CSV; replace the reader as shown to use Parquet.

## Before analyzing a research dataset

Read the release manifest, provenance, quality results, and exclusions alongside the data. Confirm that the population, task, reference side, signal definitions, and processing match your question. Inspect missing and unchecked results as well as failed checks. Existing catalog downloads are legacy / unreviewed unless accompanied by an approved release record.

Full converted data includes converted observations before profile filtering. Profile-filtered data retains observations according to named rules; inspect the rule profile and exclusions before using it. Neither variant is the original source recording.

## 1. Load and verify observation boundaries

=== "Python"

    Install dependencies once:

    ```bash
    python -m pip install pandas pyarrow matplotlib
    ```

    ```python
    import numpy as np
    import pandas as pd

    df = pd.read_csv("locohub_example_data.csv")
    # Parquet alternative: df = pd.read_parquet("locohub_example_data.parquet")
    identity = ["subject", "source_recording_id", "observation_id", "reference_side"]
    counts = df.groupby(identity, dropna=False).size()
    assert len(df) == 600 and len(counts) == 4
    assert counts.eq(150).all()
    assert not df.duplicated(identity + ["phase_ipsi"]).any()
    for _, observation in df.groupby(identity, dropna=False):
        phase = observation.sort_values("phase_ipsi")["phase_ipsi"].to_numpy()
        assert np.allclose(phase, np.linspace(0, 100, 150))
    print(counts)
    ```

=== "MATLAB"

    Use MATLAB with `readtable`; `parquetread` is needed only for the Parquet alternative.

    ```matlab
    T = readtable("locohub_example_data.csv", "TextType", "string");
    % Parquet alternative: T = parquetread("locohub_example_data.parquet");
    identity = ["subject", "source_recording_id", "observation_id", "reference_side"];
    [group, observations] = findgroups(T(:, cellstr(identity)));
    counts = splitapply(@numel, T.phase_ipsi, group);
    assert(height(T) == 600 && height(observations) == 4);
    assert(all(counts == 150));
    sampleKeys = T(:, cellstr([identity, "phase_ipsi"]));
    assert(height(unique(sampleKeys)) == height(T));
    for k = 1:height(observations)
        phase = sort(T.phase_ipsi(group == k));
        assert(all(abs(phase - linspace(0, 100, 150)') < 1e-7));
    end
    observations.sample_count = counts;
    disp(observations);
    ```

These checks establish the sample's shape and identities. They do not establish the accuracy of its signals. For real data, use the observation identity recorded in the release and check the declared observation type before averaging.

## 2. Select complete observations and inspect signal availability

=== "Python"

    ```python
    selected = df.loc[
        (df["subject"] == "EXAMPLE_01")
        & (df["task"] == "level_walking")
        & (df["observation_type"] == "individual_cycle")
    ].copy()
    signal = "knee_flexion_angle_ipsi_rad"
    assert selected.groupby(identity).size().eq(150).all()
    missing_samples = selected.groupby(identity)[signal].apply(lambda x: x.isna().sum())
    print(missing_samples)  # Zero for both synthetic observations.
    assert missing_samples.eq(0).all()
    ```

=== "MATLAB"

    ```matlab
    selected = T(T.subject == "EXAMPLE_01" & T.task == "level_walking" ...
        & T.observation_type == "individual_cycle", :);
    signal = "knee_flexion_angle_ipsi_rad";
    [selectedGroup, selectedObservations] = findgroups(selected(:, cellstr(identity)));
    assert(all(splitapply(@numel, selected.phase_ipsi, selectedGroup) == 150));
    missingSamples = splitapply(@(x) sum(ismissing(x)), selected.(signal), selectedGroup);
    disp(missingSamples);  % Zero for both synthetic observations.
    assert(all(missingSamples == 0));
    ```

Never fill unavailable research signals with zeros merely to make an array rectangular. A missing signal and a measured zero have different meanings.

## 3. Plot each observation

=== "Python"

    ```python
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    for key, observation in selected.groupby(identity, sort=True):
        observation = observation.sort_values("phase_ipsi")
        ax.plot(
            observation["phase_ipsi"],
            np.rad2deg(observation[signal]),
            label=key[2],
        )
    ax.set(xlabel="Phase (%)", ylabel="Knee flexion (degrees)", title="Synthetic example")
    ax.legend(title="Observation")
    fig.tight_layout()
    plt.show()
    ```

=== "MATLAB"

    ```matlab
    figure; hold on;
    for k = 1:height(selectedObservations)
        observation = sortrows(selected(selectedGroup == k, :), "phase_ipsi");
        plot(observation.phase_ipsi, rad2deg(observation.(signal)), ...
            "DisplayName", selectedObservations.observation_id(k));
    end
    xlabel("Phase (%)"); ylabel("Knee flexion (degrees)");
    title("Synthetic example"); legend("show"); grid on;
    ```

Angles are stored in radians; the plot converts them to degrees for display. Retain original units in exported data.

## Continue with research data

Use the [catalog](../datasets/index.md) to locate datasets, then check the [data contract](../reference/index.md). Preserve subject and source-recording identities in any analysis split. Bilateral views, repeated cycles, and ensemble curves do not create additional independent participants. Report the release identifier, chosen variant, filtering profile, exclusions, and original dataset citation with your results.
