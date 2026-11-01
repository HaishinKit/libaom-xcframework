#!/usr/bin/env python3
"""Build pinned libaom with Apple clang; no third-party runtime dependencies."""
import json, os, pathlib, shutil, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
os.chdir(ROOT)
VERSION = '3.15.3'
COMMIT = 'b141d9c45db236335351c8a4b2a14b3ade27c937'
URL = 'https://aomedia.googlesource.com/aom'
# name: SDK, clang target. Simulator deployment targets follow the sibling packages.
PLATFORMS = {
 'ios': ('iphoneos', 'arm64-apple-ios13.0'),
 'ios-simulator': ('iphonesimulator', 'arm64-apple-ios14.0-simulator'),
 'macos': ('macosx', 'arm64-apple-macos11.0'),
 'maccatalyst': ('macosx', 'arm64-apple-ios14.0-macabi'),
 'tvos': ('appletvos', 'arm64-apple-tvos13.0'),
 'tvos-simulator': ('appletvsimulator', 'arm64-apple-tvos14.0-simulator'),
 'visionos': ('xros', 'arm64-apple-xros1.0'),
 'visionos-simulator': ('xrsimulator', 'arm64-apple-xros1.0-simulator'),
}
def run(*args, **kwargs):
 return subprocess.check_output(args, text=True, **kwargs).strip()
def check_source():
 src = ROOT/'libaom'
 if run('git','-C',str(src),'rev-parse','HEAD') != COMMIT:
  raise SystemExit('Unexpected libaom revision')
 if run('git','-C',str(src),'status','--porcelain'):
  raise SystemExit('Upstream checkout must be clean')
def prepare():
 src = ROOT / 'libaom'
 if not src.exists():
  subprocess.run(['git','clone','--depth','1','--branch',f'v{VERSION}',URL,str(src)],check=True)
 check_source()
 (ROOT/'build').mkdir(exist_ok=True)
 (ROOT/'build/source.json').write_text(json.dumps({'version':VERSION,'commit':COMMIT,'url':URL,'modified':False,'configuration':{'highBitDepth':True,'realtimeOnly':False,'libyuv':False,'webmIO':False,'apps':False}},indent=2)+'\n')
def build(name):
 sdk, triple = PLATFORMS[name]
 source = ROOT/'libaom'
 if not (ROOT/'build/source.json').exists(): raise SystemExit('Run ./build.sh prepare first')
 check_source()
 directory = ROOT/'build'/name
 if directory.exists(): shutil.rmtree(directory)
 sysroot = run('xcrun','--sdk',sdk,'--show-sdk-path')
 system = {'iphoneos':'iOS','iphonesimulator':'iOS','appletvos':'tvOS','appletvsimulator':'tvOS','xros':'visionOS','xrsimulator':'visionOS','macosx':'Darwin'}[sdk]
 cmake = os.environ.get('CMAKE','cmake')
 prefix = directory/'install'
 subprocess.run([cmake,'-S',str(source),'-B',str(directory),
  '-DCMAKE_BUILD_TYPE=RelWithDebInfo','-DBUILD_SHARED_LIBS=OFF',
  f'-DCMAKE_SYSTEM_NAME={system}','-DCMAKE_SYSTEM_PROCESSOR=arm64','-DAOM_TARGET_CPU=arm64',
  '-DCMAKE_OSX_ARCHITECTURES=arm64',f'-DCMAKE_OSX_SYSROOT={sysroot}',
  f'-DCMAKE_C_COMPILER={run("xcrun","--sdk",sdk,"--find","clang")}',
  f'-DCMAKE_CXX_COMPILER={run("xcrun","--sdk",sdk,"--find","clang++")}',
  f'-DCMAKE_C_COMPILER_TARGET={triple}',f'-DCMAKE_CXX_COMPILER_TARGET={triple}',
  '-DCMAKE_C_FLAGS_RELWITHDEBINFO=-O3 -DNDEBUG -g','-DCMAKE_CXX_FLAGS_RELWITHDEBINFO=-O3 -DNDEBUG -g',
  '-DCMAKE_POSITION_INDEPENDENT_CODE=ON',f'-DCMAKE_INSTALL_PREFIX={prefix}',
  '-DENABLE_APPS=OFF','-DENABLE_TESTS=OFF','-DENABLE_EXAMPLES=OFF','-DENABLE_TOOLS=OFF','-DENABLE_DOCS=OFF',
  '-DCONFIG_AV1_ENCODER=1','-DCONFIG_AV1_DECODER=1','-DCONFIG_AV1_HIGHBITDEPTH=1',
  '-DCONFIG_REALTIME_ONLY=0','-DCONFIG_LIBYUV=0','-DCONFIG_WEBM_IO=0'],check=True)
 subprocess.run([cmake,'--build',str(directory),'--parallel',os.environ.get('JOBS','8')],check=True)
 subprocess.run([cmake,'--install',str(directory)],check=True)
 check_source()
 (directory/'source.json').write_bytes((ROOT/'build/source.json').read_bytes())
 headers = prefix/'include'
 (headers/'module.modulemap').write_text('module libaom [system] {\n  umbrella "aom"\n  export *\n}\n')
def package():
 check_source()
 args = ['xcodebuild','-create-xcframework']
 for name in PLATFORMS:
  directory = ROOT/'build'/name
  if (directory/'source.json').read_bytes() != (ROOT/'build/source.json').read_bytes():
   raise SystemExit(f'Stale build: {name}')
  args += ['-library',str(directory/'install/lib/libaom.a'),'-headers',str(directory/'install/include')]
 output = ROOT/'libaom.xcframework'
 if output.exists(): shutil.rmtree(output)
 subprocess.run(args+['-output',str(output)],check=True)
 licenses = output/'Licenses'
 licenses.mkdir()
 for name in ['LICENSE','PATENTS','AUTHORS']:
  shutil.copy2(ROOT/'libaom'/name,licenses/name)
 for dependency in ['fastfeat','vector']:
  shutil.copy2(ROOT/'libaom/third_party'/dependency/'LICENSE',licenses/(dependency+'-LICENSE'))
 shutil.copy2(ROOT/'build/source.json',licenses/'SOURCES.json')
 archive = ROOT/'libaom.xcframework.zip'
 archive.unlink(missing_ok=True)
 subprocess.run(['/usr/bin/zip','-qry',str(archive),output.name],check=True,env=dict(os.environ,COPYFILE_DISABLE='1'))
 checksum = run('swift','package','compute-checksum',str(archive))
 (ROOT/'libaom.xcframework.zip.sha256').write_text(checksum+'\n')
def release(tag):
 subprocess.run([sys.executable,str(ROOT/'scripts/release-manifest.py'),'release',tag],check=True)
command = sys.argv[1] if len(sys.argv)>1 else 'all'
if command == 'prepare': prepare()
elif command == 'build':
 for name in ([sys.argv[2]] if len(sys.argv)>2 else PLATFORMS): build(name)
elif command == 'package': package()
elif command == 'verify':
 subprocess.run([sys.executable,str(ROOT/'scripts/release-manifest.py'),'check-local'],check=True)
 subprocess.run([sys.executable,str(ROOT/'tests/verify.py')],check=True)
elif command == 'local': subprocess.run([sys.executable,str(ROOT/'scripts/release-manifest.py'),'local'],check=True)
elif command == 'release': release(sys.argv[2])
elif command == 'publish': subprocess.run([sys.executable,str(ROOT/'scripts/publish.py'),sys.argv[2]],check=True)
elif command == 'all':
 prepare()
 for name in PLATFORMS: build(name)
 package()
 shutil.copy2(ROOT/'support/Package.swift', ROOT/'Package.swift')
else: raise SystemExit('Commands: all, prepare, build [platform], package, local, release TAG, publish TAG')
