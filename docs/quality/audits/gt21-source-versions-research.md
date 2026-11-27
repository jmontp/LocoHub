# GT21 source versions: is there a newer, corrected release? (research note, 2026-11-27)

Read-only research. Nothing converted, downloaded or changed.

## Published versions and locations (primary sources)
- Paper: Camargo, Ramanathan, Flanagan, Young, J Biomech 2021, doi 10.1016/j.jbiomech.2021.110320. No erratum or corrigendum found in web searches (journal corrections page itself not checked).
- Mendeley Data, three parts, each with exactly two versions:
  - Part 1 https://data.mendeley.com/datasets/fcgm3chfff (DOI 10.17632/fcgm3chfff), Part 2 https://data.mendeley.com/datasets/k9kvm5tn3f, Part 3 https://data.mendeley.com/datasets/jj3r5f9pnf.
  - Version 1 "Published: 26 February 2021"; Version 2 "Published: 18 October 2021" (compare page https://data.mendeley.com/datasets/compare/k9kvm5tn3f).
  - The compare page shows versions 1 and 2 differ only in date and DOI; title, description, licence (CC BY 4.0) are identical. No changelog. The description reads "For more information and download with a Dropbox mirror, visit http://www.epic.gatech.edu/opensource-biomechanics-camargo-et-al/".
  - Our own Mendeley API query (GT21-S01, 2026-10-31) also found only v1 and v2 for all three parts, both before 2024.
- EPIC lab page http://www.epic.gatech.edu/opensource-biomechanics-camargo-et-al/ (also https://www.epic.gatech.edu/?p=645): "Data access is provided here with a public-view Dropbox directory"; "We recommend to download each subject individually (~1GB per subject)". No version, date, changelog or known-error text found. Dropbox: https://www.dropbox.com/sh/lhurwcy0znonh56/AAAPmVdrxh7M6FW-UYHyPHyza?dl=0 (folder CAMARGO_ET_AL_J_BIOMECH_DATASET; page content not readable by fetch).
- GitHub issues / forum posts about joint-angle, IK or model errors for this dataset: not found. Reprocessing by the same group in later papers (2023-2024): not found; the 2023 Scientific Data paper (https://www.nature.com/articles/s41597-023-02840-6) is a different dataset (GT23).

## What changed in 2024 (only in the README that ships with the Dropbox copy)
Local README (contributor_tools/.../Gtech_2021/CAMARGO_ET_AL_J_BIOMECH_DATASET/README.txt), exact lines:
- "static - Marker data collected during static trials (Included in update 4/28/2024)"
- "ik_offset - Inverse kinematics with angles relative to the angles found during the static pose. Sampled at 200Hz. (Included in update 4/28/2024)."
- "scripts/RUN_OSIM.m: Compute inverse kinematics and inverse dynamics using OpenSim models for each subject. Subject models and OpenSim configurations are found in <subject>/osimxml/. (Updated 4/28/2024)."

The local scripts/RUN_OSIM.m computes `ik_offset = ik - mean(static IK)`, with static IK from the new static marker trials run through the same subject .osim and IKSetup.xml. So the 2024 update ADDS a static-pose-referenced angle table and the static markers. It does not state that any earlier angle, joint centre, model or IK was wrong. The README says nothing about errors or fixes.

Listing evidence (GT21-S02): files dated 2024-04-08 are exactly ik_offset plus static (README says 4/28; the discrepancy is unexplained). Every ramp/id file was rewritten 2021-09-23/24 (between Mendeley v1 and v2); AB17 ramp/id has 2 size differences vs v1 (ramp_1_r_01_01, ramp_6_r_01_04). Whether the osimxml folder or the trial ik files changed in 2024: not checked. Modification times are metadata, not proof.

## Answers
(a) Newer version: Mendeley v2 (Oct 2021) is metadata-only as far as the pages show (file contents not compared). A 2024 update exists only on the authors' Dropbox/EPIC copy (adds static trials and ik_offset, updates RUN_OSIM.m). No release note says it fixes joint angles, joint centres, scaled models or IK. No fix found; "known error" not confirmed by any public source.
(b) Does it explain the knee 9-15 deg, thigh +4-7, shank -6-7 offsets? Not supported by evidence. LocoHub's segment angles come from the authors' scaled-model joint centres, which the update notes do not claim to change. One untested possibility: ik_offset subtracts the static-pose angle, so it removes any standing offset from the IK joint angles; whether that relates to the gap has not been tested. Treat as hypothesis only.
(c) Version used: the authors' 2024 copy (Dropbox) for all 22 participants; 16 local from it, 6 more acquired as ZIPs in /mnt/s/locomotion_data/gt21_author_mirror_2024 (not extracted); local README and SubjectInfo.mat are byte-identical to the Dropbox copy and differ from the Mendeley README. No publisher checksums exist for it. Only AB17 was compared with the Mendeley v1 archive (1,464 of 1,466 files equal in size; CRC-identical except 2 ramp/id files and the 2024 additions). The converter reads ik_offset for joint angles (GT21-S01); Mendeley v1 has no ik_offset.
(d) To settle it: (1) ask the authors (Camargo / EPIC lab, Young) directly whether the 2024 update or the pre-2021-09 files changed any model, joint centre or IK, and whether there is a known knee/shank offset; (2) compare osimxml (.osim, IKSetup) of one participant between the Mendeley v1/v2 archive and the Dropbox copy (AB17 v1 is already local and the 2024 AB17 is in the mirror: a small offline CRC comparison, no new download); (3) compare ik vs ik_offset vs static IK knee angles for one participant to see whether the static pose explains the knee gap; (4) check the J Biomech corrections page. Mendeley v2 would be needed only for checking ramp/id files.

Not found: erratum, corrigendum, GitHub issue, forum post, changelog beyond the README lines above, follow-up reprocessing paper.
