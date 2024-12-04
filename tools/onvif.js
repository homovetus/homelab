const { Cam } = require("onvif/promises");

const cam = new Cam({
  username: "onvif",
  password: "password!",
  hostname: "192.168.0.2",
  port: 80,
});

(async () => {
  await cam.connect();
  const input = (await cam.getStreamUri({ protocol: "RTSP" })).uri.replace(
    "://",
    `://${cam.username}:${cam.password}@`
  );
  console.log(input);
})().catch(console.error);
