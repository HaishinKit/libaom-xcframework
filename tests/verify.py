#!/usr/bin/env python3
import json, os, pathlib, plistlib, subprocess, tempfile
root = pathlib.Path(__file__).resolve().parent.parent
framework = root/'libaom.xcframework'
info = plistlib.loads((framework/'Info.plist').read_bytes())
assert len(info['AvailableLibraries']) == 8
triples = {('ios',None): ('iphoneos','arm64-apple-ios13.0'), ('ios','simulator'): ('iphonesimulator','arm64-apple-ios14.0-simulator'),
 ('ios','maccatalyst'): ('macosx','arm64-apple-ios14.0-macabi'), ('macos',None): ('macosx','arm64-apple-macos11.0'),
 ('tvos',None): ('appletvos','arm64-apple-tvos13.0'), ('tvos','simulator'): ('appletvsimulator','arm64-apple-tvos14.0-simulator'),
 ('xros',None): ('xros','arm64-apple-xros1.0'), ('xros','simulator'): ('xrsimulator','arm64-apple-xros1.0-simulator')}
with tempfile.TemporaryDirectory() as tmp:
 tmp = pathlib.Path(tmp)
 swift = tmp/'main.swift'
 swift.write_text('import libaom\nprecondition(aom_codec_av1_cx() != nil)\nprecondition(aom_codec_av1_dx() != nil)\nprint(String(cString: aom_codec_version_str()))\n')
 for lib in info['AvailableLibraries']:
  assert lib['SupportedArchitectures'] == ['arm64']
  sdk, target = triples[(lib['SupportedPlatform'],lib.get('SupportedPlatformVariant'))]
  path = framework/lib['LibraryIdentifier']
  archive = path/lib['LibraryPath']
  headers = path/lib['HeadersPath']
  sysroot = subprocess.check_output(['xcrun','--sdk',sdk,'--show-sdk-path'],text=True).strip()
  output = tmp/lib['LibraryIdentifier']
  subprocess.run(['xcrun','--sdk',sdk,'swiftc','-target',target,'-sdk',sysroot,'-module-cache-path',str(tmp/'cache'),'-I',str(headers),str(swift),str(archive),'-o',str(output)],check=True)
  if sdk == 'macosx' and 'macabi' not in target:
   subprocess.run([str(output)],check=True)
   subprocess.run(['xcrun','clang','-target',target,'-isysroot',sysroot,'-I',str(headers),str(root/'tests/roundtrip.c'),str(archive),'-o',str(tmp/'roundtrip')],check=True)
   subprocess.run([str(tmp/'roundtrip')],check=True)
  print('Linked Swift consumer:', lib['LibraryIdentifier'],flush=True)
 # Exercise actual SwiftPM binary-target selection, in addition to direct compiler links.
 consumer = tmp/'consumer'
 (consumer/'Sources/Consumer').mkdir(parents=True)
 (consumer/'Sources/Consumer/main.swift').write_text(swift.read_text())
 (consumer/'Package.swift').write_text('// swift-tools-version: 5.9\nimport PackageDescription\nlet package = Package(name: "Consumer", platforms: [.macOS(.v11)], dependencies: [.package(path: '+json.dumps(str(root))+')], targets: [.executableTarget(name: "Consumer", dependencies: [.product(name: "libaom", package: "libaom-xcframework")])])\n')
 subprocess.run(['swift','run','--package-path',str(consumer),'--scratch-path',str(tmp/'spm-build'),'--cache-path',str(tmp/'spm-cache'),'--config-path',str(tmp/'spm-config'),'--security-path',str(tmp/'spm-security'),'--disable-sandbox','Consumer'],check=True,env=dict(os.environ,CLANG_MODULE_CACHE_PATH=str(tmp/'clang-cache'),SWIFTPM_MODULECACHE_OVERRIDE=str(tmp/'swift-cache')))
print('All eight slices and SwiftPM consumer verified')
