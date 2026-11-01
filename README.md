# libaom.xcframework

libaom **3.15.3**, pinned to upstream commit
`b141d9c45db236335351c8a4b2a14b3ade27c937`, for HaishinKit and independent use.
Includes software AV1 encoding and decoding, ARM NEON optimizations, static
linking, and Release optimization with embedded DWARF debug information.
High-bit-depth support is enabled. Both general-purpose and realtime encoding
modes are available; applications select the usage and speed through the C API.
WebM file I/O and libyuv integration are disabled. No external runtime dependencies.

## Platforms

| Platform | Minimum | Architecture |
|---|---|---|
| iOS device | 13.0 | arm64 |
| iOS simulator | 14.0 | arm64 |
| macOS | 11.0 | arm64 |
| Mac Catalyst | 14.0 | arm64 |
| tvOS device | 13.0 | arm64 |
| tvOS simulator | 14.0 | arm64 |
| visionOS device and simulator | 1.0 | arm64 |

Eight XCFramework slices. Intel and watchOS are not included. Verification
covers Swift linking for every slice and 8-bit/10-bit realtime codec round trips on macOS; it does not
cover device/simulator execution, sustained realtime performance, power usage,
or final application archive validation.

## Build

Requires Xcode with all listed SDKs, Python 3, Git, and CMake 3.31.10 (the version
used by CI). No NASM is needed for arm64.

```sh
./build.sh                     # Fetch, build all slices, create XCFramework and ZIP
./build.sh verify              # Swift links, macOS AV1 round trips, SwiftPM consumer
python3 tests/verify-release.py
```

Individual operations are `prepare`, `build [platform]`, `package`, `local`,
`release TAG`, and `publish TAG`. Platform names are `ios`, `ios-simulator`,
`macos`, `maccatalyst`, `tvos`, `tvos-simulator`, `visionos`, and
`visionos-simulator`. `package` requires all eight platform builds.

Set `CMAKE=/path/to/cmake` and `JOBS=4` as needed. Each platform build starts
clean. Preparation and compilation reject an unexpected or modified upstream
checkout under `libaom/`. No upstream source patches are applied. Source revision
and configuration metadata are included with each slice and the final archive.
After changing source pins or build settings, prepare and rebuild every slice.

## Debug symbols

Static libraries retain `-O3 -DNDEBUG -g` DWARF information. They do not ship a
standalone dSYM. Archive your app with DWARF with dSYM File, retain its matching
dSYM, and upload the app's symbols through your crash-reporting workflow.

## Swift Package Manager

After building, add this directory as a local package and use the `libaom` product:

```swift
import libaom

let encoder = aom_codec_av1_cx()
let decoder = aom_codec_av1_dx()
```

Public C headers retain their `aom/` layout; the module map exports `libaom`.
The package does not add a transport or integrate AV1 into HaishinKit itself.

## Release from GitHub Actions

The intended repository is `https://github.com/HaishinKit/libaom-xcframework`.
Once the repository and these files are on `main`:

1. Open **Actions → Release XCFramework → Run workflow**.
2. Select **main** and enter a package version, such as `3.15.3`.
3. Run the workflow. Success publishes `v3.15.3` and its GitHub Release.

The input is the **package distribution version**, not the upstream libaom
version to download. Change the source pins in `scripts/build.py` separately.
`3.15.3` and `v3.15.3` normalize to `v3.15.3`. Only stable versions are accepted;
existing tags and releases (including drafts) are rejected. Release runs are
serialized.

The workflow builds all eight slices on an Apple silicon `macos-26` runner with
Xcode 26.6 and CMake 3.31.10, verifies Swift linking and macOS codec round trips,
then generates the remote Swift package manifest with the exact ZIP checksum.
It commits that manifest and pushes **only the release tag**. `main` retains its
local development manifest; remote SwiftPM consumers select a published version.

The built-in `GITHUB_TOKEN` with `contents: write` is sufficient; repository rules
must permit tag and Release creation. No personal access token or signing
secret is required. The separate **Build XCFramework** workflow uploads review
artifacts without publishing.

Before pushing the release tag, the release workflow saves the exact ZIP,
checksum, and `dist/Package.swift` as a recovery artifact for 30 days. If
publication fails after the tag is pushed, do **not** rebuild or move the tag:
download the saved artifact, check out that tag, restore the ZIP and checksum
to the repository root, and run `./build.sh publish v3.15.3`.

Publishing checks the manifest/checksum, clean working tree, matching local and
remote tags at HEAD, and notices inside the ZIP. It refuses to replace an
existing release. Inspect and complete any draft or partial Release with the
saved assets instead of overwriting them.

For a manual release, run `./build.sh release v3.15.3`, review and commit the
remote manifest, push that commit and its tag, then run `./build.sh publish v3.15.3`.
The repository and Release URL must exist before remote consumers can resolve
the package. Local release preparation never uploads anything. Restore the
local manifest with `./build.sh local` before local development or verification.

## Licenses and app redistribution

libaom uses BSD 2-Clause with the separate Alliance for Open Media Patent
License 1.0. Preserve both `LICENSE` and `PATENTS`. The patent license includes
conditions on availability of necessary patent claims and defensive termination;
it is separate from the software copyright license.

The XCFramework's `Licenses/` directory includes these texts, `AUTHORS`, source
provenance, and the applicable fastfeat (BSD 3-Clause) and vector (MIT) notices.
Preserve the notices in your app's Open Source Licenses screen or accompanying
documentation. SwiftPM does not automatically copy the top-level `Licenses/`
directory into your app. Check the original texts and included notices for the
exact version being distributed.

The build scripts in this repository use the BSD 3-Clause license in `LICENSE.md`.
