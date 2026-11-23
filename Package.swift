// swift-tools-version: 5.9
import PackageDescription
let package = Package(
    name: "libaom",
    platforms: [.iOS(.v13), .tvOS(.v13), .macOS(.v11), .macCatalyst(.v14), .visionOS(.v1)],
    products: [.library(name: "libaom", targets: ["libaom"])],
    targets: [.binaryTarget(name: "libaom", url: "https://github.com/HaishinKit/libaom-xcframework/releases/download/v3.15.4/libaom.xcframework.zip", checksum: "cc8f7346e7689ceb7e86306af5c262fb829e8d159225ac3c63ebdeb213279642")]
)
