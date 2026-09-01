## Settings – System & Quality Settings Page

![settings.png](settings.png)


This page allows administrators to configure system-level Docker engine resources and to define the thresholds used to evaluate code quality risks (bugs, code smells, vulnerabilities, etc.) for products managed in CodeWeTrust. It is accessed via **Products > Settings** in the top navigation.

### Top Navigation Bar

- **CODE WE TRUST logo** – Located at the top-left; clicking it typically returns the user to the application home/dashboard.
- **Products dropdown** – Opens a menu to navigate to the list of products or switch between products.
- **Manual** – Opens the user manual/documentation for the application.
- **Help** – Opens contextual help resources.
- **Add product** – Button with a plus icon; used to create/register a new product in the system.
- **Settings** – Icon and label for accessing the application/product settings page (the current page).
- **Saba Ghani (user menu)** – Displays the currently logged-in user's name; clicking the dropdown arrow next to it likely opens account options such as profile settings or logout.

### Breadcrumb and Page Header

- **Products** breadcrumb link – Located above the page title; clicking it navigates back to the Products list.
- **Settings** heading – Identifies the current page.
- **Help toggle** – A blue pill-shaped switch labeled "Help" next to the page title; toggling it likely shows/hides inline help or guidance text throughout the settings page.
- **Save button** – Located at the top-right of the page; used to persist any changes made to the settings on this page.

### Left-Hand Settings Navigation Menu

A vertical list of settings categories, each with an icon. Clicking any item loads its corresponding configuration panel in the main content area:

- **System** – (currently selected) Displays Docker engine resource settings.
- **Quality Settings** – Configure thresholds for code risk evaluation (partially visible below the System section).
- **Technical Debt** – Settings related to tracking and managing technical debt metrics.
- **AI Readiness** – Settings related to AI readiness evaluation of code.
- **Code Analysis Rules** – Configure rules used for code analysis/scanning.
- **Access Control** – Manage user permissions and roles.
- **API Access Tokens** – Manage tokens used for API authentication.
- **AI** – General AI-related configuration options.
- **License Discovery** – Settings for detecting and managing software licenses in code.
- **Logs** – View or configure system/application logs.
- **Maintenance** – Options related to system maintenance tasks.
- **Import & Export** – Tools to import or export settings/data.
- **Package Feeds** – Manage package feed sources used for dependency scanning.

### System Section (Main Panel)

- **Section title "System"** with subtitle **"Docker Engine Settings"** – Indicates this panel shows the resource allocation for the Docker engine used by the application.
- **CPUs field** – Displays the number of CPUs allocated to Docker (currently "4"). Read-only display showing current allocation.
- **Subnet field** – Displays the Docker network subnet in use (currently "172.17.0.0/16"). Read-only informational field.
- **Memory field** – Displays the amount of memory allocated to Docker (currently "17 GB"). Read-only informational field.
- **Disk Space field** – Displays the disk space allocated to Docker (currently "20 GB"). Read-only informational field.

These four fields appear to be status/informational displays rather than editable inputs, showing the current Docker environment resources being used by the application's scanners and analyzers.

### Quality Settings Section (Main Panel)

- **Section title "Quality Settings"** with subtitle **"Set up the impact of code risks evaluation findings"** – Introduces the purpose of this section: defining thresholds that determine how code risk findings are evaluated.
- **Import link** – Allows the user to import a preset configuration of quality thresholds from an external source or file.
- **Reset link** – Resets the threshold values back to default settings.
- **Default column** – A reference column showing the system's default threshold values (e.g., Bugs: 20, Code Smells: 200, Vulnerabilities: 0.5) for comparison; appears to be read-only/disabled (greyed out).
- **Imported Preset column** – A reference column showing threshold values from an imported preset (currently all zeros); appears read-only/disabled, populated only after using the Import function.
- **Select industry dropdown** – Allows the user to choose an industry category, likely to auto-populate recommended threshold values relevant to that industry's standards.

#### Threshold Rows

Each threshold row includes a label, a slider, and a numeric input box that are linked together — dragging the slider updates the number field, and vice versa:

- **Bugs Threshold (per 10K LOC)** – Slider and input box (currently set to 1000) to define the acceptable number of bugs per 10,000 lines of code before it is flagged as a risk.
- **Code Smells Threshold (per 10K LOC)** – Slider and input box (currently set to 941) to define the acceptable number of code smells per 10,000 lines of code.
- **Vulnerabilities Threshold (per 10K LOC)** – Slider and input box (currently set to 100, row partially cut off at bottom of screenshot) to define the acceptable number of vulnerabilities per 10,000 lines of code.

### Right-Hand Help Panel

- **SYSTEM tab** – Selected/active tab showing help content related to the System settings section.
- **DOCKER tab** – Alternate tab that presumably displays help content specific to Docker configuration.
- **Help text block** – Under the heading "System," explains that the CodeWeTrust application uses Docker to run code scanners and analyzers, and recommends allocating at least 2 CPUs and 8 GB of memory to the Docker engine for proper operation