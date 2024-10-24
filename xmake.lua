add_rules("mode.debug", "mode.release")
add_requires("pkgconfig::gstreamer-1.0")
add_requires("pkgconfig::gstreamer-rtp-1.0")

target("console") do
    set_kind("binary")
    add_files("rtcp.c")
    add_packages("pkgconfig::gstreamer-1.0")
    add_packages("pkgconfig::gstreamer-rtp-1.0")
    add_ldflags("-lgstcodecparsers-1.0", {force=true})
    if is_mode("debug") then
        add_defines("DEBUG")
    end
end
