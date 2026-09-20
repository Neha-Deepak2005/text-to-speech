export default function AudioPlayer({ src }) {
  if (!src) return null;

  return (
    <div>
      <p className="mb-1 text-sm font-medium text-slate-700">Generated Audio</p>
      {/* Native <audio> controls already provide play/pause/seek/volume. */}
      <audio controls src={src} className="w-full">
        Your browser does not support the audio element.
      </audio>
    </div>
  );
}
