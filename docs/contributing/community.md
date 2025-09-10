# Community & Support

Join a growing community of biomechanics researchers working together to make data more accessible.

---

## Getting Help

### Where to Ask Questions

!!! info "Support Channels"
    **[GitHub Discussions](https://github.com/your-repo/discussions)**  
    For general questions, conversion help, and community discussion
    
    **[GitHub Issues](https://github.com/your-repo/issues)**  
    For bug reports and feature requests
    
    **Response Time**: Usually within 24 hours

### Writing Good Questions

Help us help you by providing:

!!! example "Good Question Format"
    **Title**: Clear, specific description
    
    **Context**:
    - What data source you're working with
    - What step you're on
    - What you've already tried
    
    **Details**:
    - Error messages (if any)
    - Code snippets
    - Sample data structure
    
    **Example**: "Converting Vicon data - knee angles failing validation at 75% phase"

### Common Questions Answered

??? question "My validation is failing - what should I do?"
    1. Check units (radians vs degrees is the most common issue)
    2. Verify sign conventions match the standard
    3. Look at the specific phase where failure occurs
    4. Consider if you need custom validation ranges for your population

??? question "How do I handle missing data?"
    - NaN values are acceptable for missing time points
    - If entire variables are missing, just omit those columns
    - Document any systematic missing data in your README

??? question "Can I use left/right instead of ipsi/contra?"
    Yes, but be consistent. The standard supports both:
    - `knee_flexion_angle_ipsi_rad` / `knee_flexion_angle_contra_rad`
    - `knee_flexion_angle_left_rad` / `knee_flexion_angle_right_rad`

??? question "What coordinate system should I use?"
    Follow ISB recommendations where possible. See our [biomechanical standard](../reference/biomechanical_standard/) for details.

---

## Contributing Back

### Share Your Conversion Script

Once your conversion works, help others with similar data:

1. **Clean up your script** - Remove hardcoded paths, add comments
2. **Add documentation** - Include a README with:
   - Data source description
   - Any assumptions made
   - Special handling required
3. **Submit a pull request** to `contributor_tools/conversion_scripts/YourDataset/`

!!! example "Good Conversion Script Structure"
    ```
    contributor_tools/conversion_scripts/YourLab_2024/
    ├── README.md                     # Documentation
    ├── convert_to_parquet.py         # Main conversion script
    ├── requirements.txt              # Python dependencies
    └── example_raw_data_structure.txt # Show input format
    ```

### Documentation Contributions

Help improve the documentation:
- Fix typos or unclear explanations
- Add examples from your experience
- Translate to other languages
- Create video tutorials

### Reporting Issues

Found a bug? Let us know:

!!! bug "Report a Bug"
    1. Check if already reported in [Issues](https://github.com/your-repo/issues)
    2. Create a new issue with:
       - Clear title
       - Steps to reproduce
       - Expected vs actual behavior
       - Your environment (OS, Python version, etc.)

---

## Who's Using This

### Current Datasets

| Institution | Dataset | Subjects | Tasks | Year |
|------------|---------|----------|-------|------|
| University of Michigan | umich_2021 | 10 | Walking, inclines | 2021 |
| Georgia Tech | gtech_2021 | 15 | Walking, stairs | 2021 |
| *Your institution* | *Your dataset* | - | - | - |

### Success Stories

!!! quote "Researcher Feedback"
    "The standardization saved us months of work. We could immediately compare our Parkinson's data with healthy controls from other labs."
    
    — Clinical Biomechanics Lab

!!! quote "Collaboration Example"
    "Three labs combined datasets for a 100+ subject study on aging. The standardized format made it trivial."
    
    — Multi-site Aging Study

### Publications Using Standardized Data

- Example Paper 1 (2024) - *Journal of Biomechanics*
- Example Paper 2 (2024) - *Gait & Posture*
- [Add your publication](https://github.com/your-repo/discussions)

---

## Citation

If you use the standardized datasets or tools in your research:

!!! cite "Citation"
    ```bibtex
    @software{locomotion_standards_2024,
      title = {Locomotion Data Standardization Framework},
      author = {LocoHub Contributors},
      year = {2024},
      url = {https://github.com/your-repo}
    }
    ```

Also cite the original data sources:
- UMich 2021: [Reznick et al., 2021](https://doi.org/10.1038/s41597-021-01057-9)
- GTech 2021: [Citation pending]

---

## Join the Movement

### Ways to Participate

=== "Contribute Data"
    Share your standardized datasets to help the community grow
    
    [Start Converting](getting_started.md){ .md-button }

=== "Improve Tools"
    Help develop better conversion and validation tools
    
    [View on GitHub](https://github.com/your-repo){ .md-button }

=== "Spread the Word"
    Share with colleagues who might benefit
    
    Present at conferences, write blog posts, or give talks

### Stay Updated

- **Watch** the [GitHub repository](https://github.com/your-repo) for updates
- **Join** discussions for announcements
- **Follow** contributors on social media

---

## Code of Conduct

We're committed to providing a welcoming and inclusive environment.

!!! important "Community Guidelines"
    - **Be respectful** of different experience levels
    - **Be constructive** in feedback and criticism
    - **Be patient** with questions - we were all beginners once
    - **Be generous** in sharing knowledge and credit
    
    Full [Code of Conduct](https://github.com/your-repo/blob/main/CODE_OF_CONDUCT.md)

---

<div class="next-steps" markdown>
**Ready to contribute?**

[**Start Converting**](getting_started.md){ .md-button .md-button--primary }
[**Ask a Question**](https://github.com/your-repo/discussions){ .md-button }
</div>