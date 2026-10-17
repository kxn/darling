# Intel Xcode on Linux: source checkpoint

This fork preserves experimental Darling source changes as of 2026-10-17.

- [Workspace, scripts, tests, source restoration and progress](https://github.com/kxn/darling/tree/linuxcode/workspace-2026-10-17)
- Modified submodules point to the matching commits in kxn's upstream forks. Other submodules retain their upstream URLs.
- The original xcodebuild starts SwiftBuild and executes build-description, header-map and response-file tasks. A full project build still fails at clang-stat-cache: FSEventsGetCurrentEventId is missing. Source compilation through xcodebuild, linking, Unity/CocoaPods, archive, signing and export are not complete.
- Progress with the project build uses an explicitly permissive diagnostic CoreServices policy. Strict sandbox enforcement is incomplete.
- No Xcode, Apple SDK, extracted Apple system images, runtime trees or signing credentials are included.

These commits are a reviewable research checkpoint, not a claim of production Xcode compatibility or a full upstream build passing. See the workspace branch for exact original base revisions, patches, historical scripts and limitations.
