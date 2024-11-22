const server = require('http').createServer((req, res) =>
        res.end(`
<!DOCTYPE html><body>
<canvas width='640' height='480' />
<script src="/socket.io/socket.io.js"></script><script>
  const socket = io(), ctx = document.getElementsByTagName('canvas')[0].getContext('2d');
  socket.on('data', (data) => {
    const img = new Image;
    const url = URL.createObjectURL(new Blob([new Uint8Array(data)], {type: 'application/octet-binary'}));
    img.onload = () => {
      URL.revokeObjectURL(url, {type: 'application/octet-binary'});
      ctx.drawImage(img, 100, 100);
    };
    img.src = url;
  });
</script></body></html>`));
const { Cam } = require('onvif/promises'), io = require('socket.io')(server), rtsp = require('rtsp-ffmpeg');

server.listen(6147);

const cam = new Cam({username: 'onvif', password: 'password!', hostname: '192.168.0.13', port: 80});

(async() => {
  await cam.connect();
  const input = (await cam.getStreamUri({protocol:'RTSP'})).uri.replace('://', `://${cam.username}:${cam.password}@`);
  console.log(input)
  const stream = new rtsp.FFMpeg({input, resolution: '320x240', quality: 3});

  io.on('connection', (socket) => {
    const pipeStream = socket.emit.bind(socket, 'data');
    stream.on('disconnect', () => stream.removeListener('data', pipeStream)).on('data', pipeStream);
  });
})().catch(console.error);
