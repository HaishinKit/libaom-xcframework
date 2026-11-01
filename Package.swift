// swift-tools-version: 5.9
import PackageDescription
let package = Package(
    name: "libaom",
    platforms: [.iOS(.v13), .tvOS(.v13), .macOS(.v11), .macCatalyst(.v14), .visionOS(.v1)],
    products: [.library(name: "libaom", targets: ["libaom"])],
    targets: [.binaryTarget(name: "libaom", url: "https://github.com/HaishinKit/libaom-xcframework/releases/download/v3.15.3/libaom.xcframework.zip", checksum: "a6dd4f65cb772770f2dcded2d72076c84dd7e5220dbb4b0b6813454e0f77e7a7")]
)
