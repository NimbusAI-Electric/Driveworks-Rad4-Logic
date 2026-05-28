# DriveWorks Reorganization Plan

This document outlines the proposed architectural reorganization for the `N:\Driveworks` folder based on our audit. Our goal is to streamline the folder hierarchy while preserving the relative path integrity required by DriveWorks internal references.

## User Review Required

> [!WARNING]
> Please review the proposed folder structure carefully. Moving `.driveprojx` files can break internal references if child project paths or specification paths are absolute instead of relative. 
> Ensure `AdditionalFoldersRelativeToSpecificationFolder` and `DocumentsRelativeToSpecificationFolder` are enabled in your projects.

## Open Questions

> [!IMPORTANT]
> 1. Do you have any active ODBC connections or hardcoded SQL paths that point specifically to `N:\Driveworks\Projects`?
> 2. The `Test` folders contain many historical testing environments (e.g., `Carlos Test`). Should these be archived into a `Legacy_Archive` folder or completely deleted?
> 3. Does the proposed categorization (JS3 Ecosystem vs. Gen4 Ecosystem vs. Standalone) accurately reflect how your engineering team conceptualizes these product lines?

## Proposed Changes

We will group files into logical ecosystems (e.g., JS3, Gen4) to isolate dependencies. Shared assets (Groups, Macros) will have their own dedicated space.

### 1. Root & Shared Assets

Consolidating group files and shared data.
#### [NEW] `N:\Driveworks\Group_Data`
#### [NEW] `N:\Driveworks\Reference`
#### [MODIFY] Move existing ODBC, Group Macros, and .drivegroup files to `Group_Data`

---

### 2. JS3 Ecosystem

Moving the JS3 hierarchy into a dedicated folder. Since JS3 Parent references Chassis and Mirror, keeping them in a unified sub-tree ensures relative paths (`..\JS3 Chassis`, `..\JS3 Mirror`) can easily be adjusted or maintained if they use adjacent relative linking.
#### [NEW] `N:\Driveworks\Products_JS3`
#### [MODIFY] Move `JS3` to `Products_JS3\Parent`
#### [MODIFY] Move `JS3 Chassis` to `Products_JS3\Chassis`
#### [MODIFY] Move `JS3 Mirror` to `Products_JS3\Mirror`

---

### 3. Gen4 Ecosystem

Isolating Generation 4 logic.
#### [NEW] `N:\Driveworks\Products_Gen4`
#### [MODIFY] Move `Gen4` to `Products_Gen4\Parent`
#### [MODIFY] Move `Gen4 Mirror` to `Products_Gen4\Mirror`

---

### 4. Standalone Products

Moving independent product line configurators.
#### [NEW] `N:\Driveworks\Products_Standalone`
#### [MODIFY] Move `Radiance` to `Products_Standalone\Radiance`
#### [MODIFY] Move `Round-Mirrors` to `Products_Standalone\Round-Mirrors`
#### [MODIFY] Move `Spark` to `Products_Standalone\Spark`
#### [MODIFY] Move `RAD3` to `Products_Standalone\RAD3`

---

### 5. Archiving

Cleaning up the root directory.
#### [NEW] `N:\Driveworks\Legacy_Archive`
#### [MODIFY] Move `805XX-TEST`, `Carlos Test`, `JS`, and other unneeded root projects here.

## Verification Plan

### Automated Tests
- Run `Get-ChildItem` to verify that all `.driveprojx` files have been moved correctly.
- We will script the moves using PowerShell to ensure no data is lost and that we only touch files explicitly listed.

### Manual Verification
- **You will need to open the JS3 Parent project** in DriveWorks Administrator to ensure it successfully locates the JS3 Chassis and JS3 Mirror child projects. If links are broken, we will use the DriveWorks Data Management tool to repath them.
