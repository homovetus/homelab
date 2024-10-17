add_rules("mode.debug", "mode.release")
add_requires("pkgconfig::gstreamer-1.0")
add_requires("pkgconfig::gstreamer-plugins-bad-1.0")

target("console") do
    set_kind("binary")
    add_files("helloworld.c")
    add_packages("pkgconfig::gstreamer-1.0")
    add_packages("pkgconfig::gstreamer-plugins-bad-1.0")
    if is_mode("debug") then
        add_defines("DEBUG")
    end
end
