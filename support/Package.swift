// swift-tools-version: 5.9
import PackageDescription
let package = Package(
    name: "libaom",
    platforms: [.iOS(.v13), .tvOS(.v13), .macOS(.v11), .macCatalyst(.v14), .visionOS(.v1)],
    products: [.library(name: "libaom", targets: ["libaom"])],
    targets: [.binaryTarget(name: "libaom", path: "libaom.xcframework")]
)
