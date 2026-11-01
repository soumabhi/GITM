import { useEffect, useState } from "react";

export function Motion({ clip, speed, maxH = 200, maxW = 280 }) {
  const [frames, setFrames] = useState([]);
  const [index, setIndex] = useState(0);
  useEffect(() => {
    let cancel = false;
    const image = new Image();
    image.onload = () => {
      const width = clip.frameWidth || image.width;
      const height = clip.frameHeight || image.height;
      const count = Math.max(1, clip.frames || Math.floor(image.width / width));
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext("2d");
      const urls = [];
      for (let frame = 0; frame < count; frame += 1) {
        context.clearRect(0, 0, width, height);
        context.drawImage(image, frame * width, 0, width, height, 0, 0, width, height);
        urls.push(canvas.toDataURL("image/png"));
      }
      if (!cancel) {
        setFrames(urls);
        setIndex(0);
      }
    };
    image.src = clip.src;
    return () => {
      cancel = true;
    };
  }, [clip.src, clip.frameWidth, clip.frameHeight, clip.frames]);
  const gap = Math.max(30, Math.round((2500 / Math.max(1, frames.length)) * (100 / (Number(speed) || 100))));
  useEffect(() => {
    if (frames.length < 2) return undefined;
    const handle = setInterval(() => setIndex((current) => (current + 1) % frames.length), gap);
    return () => clearInterval(handle);
  }, [frames, gap]);
  const height = clip.frameHeight || 1;
  const width = clip.frameWidth || 1;
  const scale = Math.min(maxH / height, maxW / width);
  return (
    <span className="figure" style={{ width: Math.round(width * scale), height: Math.round(height * scale) }}>
      {frames[index] ? <img alt="" src={frames[index]} /> : null}
    </span>
  );
}
