# Static Analysis – Charts

## Overview
This view displays the **Charts** page within the Static Analysis section for the "ansible" product. It provides a visual breakdown of code issues across the project's directory structure, allowing users to identify where issues are concentrated by directory and file, using a sunburst-style chart.

## Top Navigation Bar
- **Code We Trust logo (top-left):** Clicking this likely returns the user to the platform's home/dashboard.
- **Products:** A dropdown menu for navigating to or switching between different products tracked in the platform.
- **Manual:** Opens documentation or a help manual for the platform.
- **Help:** Opens a help resource or support option.
- **Add product:** A button to register or onboard a new product into the platform.
- **Settings:** Opens configuration options for the platform or account.
- **Saba Ghani (user menu):** Displays the logged-in user's name; clicking likely opens account settings, profile options, or logout.

## Breadcrumb and Page Header
- **Products > ansible:** Breadcrumb navigation showing the current location; clicking "Products" returns to the products list, while "ansible" refers to the current product page.
- **ansible (page title with external link icon):** Displays the name of the current product. The small external-link icon likely opens the product's external repository or source link in a new tab.
- **Reports & Exports button:** Allows the user to generate or download reports/exports related to this product's data.
- **"..." (more options) icon:** Opens additional actions or settings related to the product, not otherwise visible on this page.

## Product Tabs
A horizontal tab bar allows navigation between different analysis categories for the "ansible" product:
- **Tech Stack:** Shows technology/language composition (green check indicates healthy status).
- **Dev Team:** Displays contributor/team-related data.
- **Static Analysis (active tab):** Currently selected tab, showing code quality and issue analysis. The orange warning icon suggests attention is needed in this area.
- **Security:** Shows security-related scan results.
- **Licenses and Packages:** Displays license compliance and package dependency information.
- **Tech Debt:** Shows technical debt metrics.
- **AI Readiness:** Indicates how prepared the codebase is for AI-related processes.
- **AI Assistant:** Likely provides AI-powered insights or recommendations (denoted by a sparkle icon).
- **Benchmark:** Compares this product's metrics against benchmarks or other projects.
- **Scan Status:** Shows the status/history of code scans, with an info icon for additional details on hover.

## Left Sidebar (Static Analysis Sub-navigation)
This sidebar lists sub-sections within Static Analysis:
- **Charts (active):** Currently selected page, showing visual issue distribution charts.
- **Overview:** Likely provides a summary of static analysis results.
- **Code Quality Details:** Shows detailed code quality findings.
- **Duplicated Blocks:** Highlights duplicated code segments.
- **Time Trends:** Shows how code quality metrics change over time.
- **Frequent Issues:** Lists the most commonly occurring issues.
- **Code Risks Charts:** Visualizes code risk data.
- **Code Risks Overview:** Summarizes code risk findings.
- **Hardcoded Tokens:** Flags instances of hardcoded credentials or tokens in the code.
- **Code Risks Trends:** Shows how code risk metrics evolve over time.

## Filter Controls
Located above the chart, these dropdowns allow the user to refine the data displayed:
- **Issue Type: All (dropdown):** Filters the chart by category of issue (e.g., bug, vulnerability, code smell). Currently set to show all types.
- **Severity: Major (dropdown, with "X" to clear):** Filters issues by severity level (e.g., Major, Minor, Critical). The "X" allows the user to remove this filter and reset it.
- **Threshold: 1000 (dropdown):** Sets a numerical threshold, likely controlling the minimum size or issue count required for a directory/segment to be displayed or highlighted in the chart.

## Export Control
- **Export (png) button:** Allows the user to download the currently displayed chart as a PNG image file for reporting or sharing purposes.

## Main Chart: "All Issues Per Directory"
- **Chart Title and Subtitle:** Labeled "All Issues Per Directory," with a subtitle clarifying that "Segment size = lines of code, Color = issue density." This tells the user how to interpret the visualization.
- **Sunburst/Radial Chart:** A circular, multi-ring chart representing the project's directory structure:
  - **ROOT (center label above chart):** Indicates the top-level starting point of the directory hierarchy.
  - **Center circle:** Represents the root directory of the codebase.
  - **Inner ring segment "[root]":** Represents the top-level directory grouping directly under root.
  - **Outer ring segments (e.g., "support/ansible," "lib," "integration," "test," "units"):** Represent subdirectories within the project. Each segment's size corresponds to the number of lines of code in that directory, while the color (in this case, uniformly green) reflects issue density based on the selected filters.
  - **Hovering or clicking segments:** Although not explicitly shown as active in this screenshot, such radial charts typically allow users to hover over or click a segment to drill down into a specific directory or view more detailed issue information for that path.