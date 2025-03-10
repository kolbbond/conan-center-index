from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, rmdir, save, copy
from conan.tools.microsoft import is_msvc, is_msvc_static_runtime
from conan.tools.scm import Version
import os
import textwrap

required_conan_version = ">=1.53.0"


class SfmlConan(ConanFile):
    name = "sfml"
    description = "Simple and Fast Multimedia Library."
    license = "Zlib"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://www.sfml-dev.org"
    topics = ("multimedia", "games", "graphics", "audio")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "window": [True, False],
        "graphics": [True, False],
        "network": [True, False],
        "audio": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "window": True,
        "graphics": True,
        "network": True,
        "audio": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.window:
            # FIXME: use cci's glad
            if self.settings.os in ["Windows", "Linux", "FreeBSD", "Macos"]:
                self.requires("opengl/system")
            if self.settings.os == "Linux":
                self.requires("libudev/system")
                self.requires("xorg/system")
        if self.options.graphics:
            self.requires("freetype/2.13.2")
            self.requires("stb/cci.20230920")
        if self.options.audio:
            self.requires("flac/1.4.3")
            self.requires("openal-soft/1.22.2")
            self.requires("vorbis/1.3.7")
            if Version(self.version) >= "2.6.0":
                self.requires("minimp3/cci.20211201")

    def validate(self):
        if self.settings.os not in ["Windows", "Linux", "FreeBSD", "Android", "Macos", "iOS"]:
            raise ConanInvalidConfiguration(f"{self.ref} not supported on {self.settings.os}")
        if self.options.graphics and not self.options.window:
            raise ConanInvalidConfiguration("sfml:graphics=True requires sfml:window=True")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # sfml/2.6.0 uses minimp3 and glad in extlibs
        if Version(self.version) < "2.6.0":
            rmdir(self, os.path.join(self.source_folder, "extlibs"))

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["SFML_DEPENDENCIES_INSTALL_PREFIX"] = self.package_folder.replace("\\", "/")
        tc.cache_variables["SFML_MISC_INSTALL_PREFIX"] = os.path.join(self.package_folder, "licenses").replace("\\", "/")
        tc.variables["SFML_BUILD_WINDOW"] = self.options.window
        tc.variables["SFML_BUILD_GRAPHICS"] = self.options.graphics
        tc.variables["SFML_BUILD_NETWORK"] = self.options.network
        tc.variables["SFML_BUILD_AUDIO"] = self.options.audio
        tc.variables["SFML_INSTALL_PKGCONFIG_FILES"] = False
        tc.variables["SFML_GENERATE_PDB"] = False
        tc.variables["SFML_USE_SYSTEM_DEPS"] = True
        tc.variables["WARNINGS_AS_ERRORS"] = False
        if Version(self.version) >= "2.6.0":
            tc.variables["CMAKE_CXX_STANDARD"] = 11
        if is_msvc(self):
            tc.variables["SFML_USE_STATIC_STD_LIBS"] = is_msvc_static_runtime(self)
        tc.generate()
        deps = CMakeDeps(self)
        if Version(self.version) >= "2.6.2":
            if self.options.audio:
                deps.set_property("vorbis", "cmake_file_name", "VORBIS")
            if self.options.graphics:
                deps.set_property("freetype", "cmake_file_name", "Freetype")
                deps.set_property("freetype", "cmake_additional_variables_prefixes", ["FREETYPE"])
                deps.set_property("freetype", "cmake_target_name", "Freetype")
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        if Version(self.version) >= "2.6.0":
            copy(self, pattern="license.md", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    @property
    def _sfml_components(self):
        def gdi32():
            return ["gdi32"] if self.settings.os == "Windows" else []

        def winmm():
            return ["winmm"] if self.settings.os == "Windows" else []

        def ws2_32():
            return ["ws2_32"] if self.settings.os == "Windows" else []

        def dl():
            return ["dl"] if self.settings.os in ["Linux", "FreeBSD"] and Version(self.version) >= "2.6.0" else []

        def libudev():
            return ["libudev::libudev"] if self.settings.os == "Linux" else []

        def xorg():
            return ["xorg::xorg"] if self.settings.os == "Linux" else []

        def pthread():
            return ["pthread"] if self.settings.os in ["Linux", "FreeBSD"] else []

        def rt():
            return ["rt"] if self.settings.os in ["Linux", "FreeBSD"] else []

        def usbhid():
            return ["usbhid"] if self.settings.os == "FreeBSD" else []

        def android():
            return ["android"] if self.settings.os == "Android" else []

        def log():
            return ["log"] if self.settings.os == "Android" else []

        def foundation():
            return ["Foundation"] if is_apple_os(self) else []

        def appkit():
            return ["AppKit"] if self.settings.os == "Macos" else []

        def carbon():
            return ["Carbon"] if self.settings.os == "Macos" else []

        def iokit():
            return ["IOKit"] if self.settings.os == "Macos" else []

        def coreservices():
            return ["CoreServices"] if self.settings.os == "Macos" else []

        def coregraphics():
            return ["CoreGraphics"] if self.settings.os == "iOS" else []

        def coremotion():
            return ["CoreMotion"] if self.settings.os == "iOS" else []

        def quartzcore():
            return ["QuartzCore"] if self.settings.os == "iOS" else []

        def uikit():
            return ["UIKit"] if self.settings.os == "iOS" else []

        def opengl():
            return ["opengl::opengl"] if self.settings.os in ["Windows", "Linux", "FreeBSD", "Macos"] else []

        def opengles_android():
            return ["EGL", "GLESv1_CM"] if self.settings.os == "Android" else []

        def opengles_ios():
            return ["OpenGLES"] if self.settings.os == "iOS" else []

        def objc():
            return ["-ObjC"] if not self.options.shared and self.settings.os == "Macos" else []

        suffix = "" if self.options.shared else "-s"
        suffix += "-d" if self.settings.build_type == "Debug" else ""

        sfml_components = {
            "system": {
                "target": "sfml-system",
                "libs": [f"sfml-system{suffix}"],
                "system_libs": winmm() + pthread() + rt() + android() + log(),
            },
        }
        if self.settings.os in ["Windows", "Android", "iOS"]:
            sfml_main_suffix = "-d" if self.settings.build_type == "Debug" else ""
            sfmlmain_libs = [f"sfml-main{sfml_main_suffix}"]
            if self.settings.os == "Android":
                sfmlmain_libs.append(f"sfml-activity{suffix}")
            sfml_components.update({
                "main": {
                    "target": "sfml-main",
                    "libs": sfmlmain_libs,
                    "system_libs": android() + log(),
                },
            })
        if self.options.window:
            sfml_components.update({
                "window": {
                    "target": "sfml-window",
                    "libs": [f"sfml-window{suffix}"],
                    "requires": ["system"] + opengl() + xorg() + libudev(),
                    "system_libs": dl() + gdi32() + winmm() + usbhid() + android() + opengles_android(),
                    "frameworks": foundation() + appkit() + iokit() + carbon() +
                                  uikit() + coregraphics() + quartzcore() +
                                  coreservices() + coremotion() + opengles_ios(),
                    "exelinkflags": objc(),
                },
            })
        if self.options.graphics:
            sfml_components.update({
                "graphics": {
                    "target": "sfml-graphics",
                    "libs": [f"sfml-graphics{suffix}"],
                    "requires": ["window", "freetype::freetype", "stb::stb"],
                },
            })
        if self.options.network:
            sfml_components.update({
                "network": {
                    "target": "sfml-network",
                    "libs": [f"sfml-network{suffix}"],
                    "requires": ["system"],
                    "system_libs": ws2_32(),
                },
            })
        if self.options.audio:
            audio_requires = ["system", "flac::flac", "openal-soft::openal-soft", "vorbis::vorbis"]
            if Version(self.version) >= "2.6.0":
                audio_requires.append("minimp3::minimp3")
            sfml_components.update({
                "audio": {
                    "target": "sfml-audio",
                    "libs": [f"sfml-audio{suffix}"],
                    "requires": audio_requires,
                    "system_libs": android(),
                },
            })

        return sfml_components

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SFML")
        self.cpp_info.set_property("pkg_config_name", "sfml-all")

        def _register_components(components):
            defines = [] if self.options.shared else ["SFML_STATIC"]
            for component, values in components.items():
                target = values.get("target", [])
                libs = values.get("libs", [])
                requires = values.get("requires", [])
                system_libs = values.get("system_libs", [])
                frameworks = values.get("frameworks", [])
                exelinkflags = values.get("exelinkflags", [])
                # TODO: Properly model COMPONENTS names in CMakeDeps for find_package() call
                #       (see https://github.com/conan-io/conan/issues/10258)
                #       It should be:
                #         find_package(SFML REQUIRED COMPONENTS system window graphics network audio)
                #         target_link_libraries(myApp sfml-system sfml-window sfml-graphics sfml-network sfml-audio)
                #       Do not use cmake_target_aliases to model this, names are too generic!
                self.cpp_info.components[component].set_property("cmake_target_name", target)
                self.cpp_info.components[component].set_property("pkg_config_name", target)
                self.cpp_info.components[component].libs = libs
                self.cpp_info.components[component].defines = defines
                self.cpp_info.components[component].requires = requires
                self.cpp_info.components[component].system_libs = system_libs
                self.cpp_info.components[component].frameworks = frameworks
                self.cpp_info.components[component].exelinkflags = exelinkflags

        _register_components(self._sfml_components)
