add_rules("mode.debug", "mode.release")
add_requires("pkgconfig::gstreamer-1.0")
add_requires("pkgconfig::gstreamer-rtp-1.0")

target("recorder") do
    set_kind("binary")
    set_warnings("all")
    add_files("recorder.c")
    add_packages("pkgconfig::gstreamer-1.0")
    add_packages("pkgconfig::gstreamer-rtp-1.0")
    add_links("gstcodecparsers-1.0")
    if is_mode("debug") then
        add_defines("DEBUG")
    end
end
