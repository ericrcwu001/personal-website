import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from "react";

export type IntroFilmHandle = {
  /** Seek the film. `progress` is 0..1 across the whole master. */
  setTravel: (progress: number) => void;
};

type IntroFilmProps = {
  onReady?: () => void;
};

/** Runtime of the encoded master, in seconds. Keep in sync with the media files. */
export const FILM_DURATION = 29;

/** Master is encoded at 12fps; one frame is the smallest meaningful seek. */
const FRAME = 1 / 12;

/**
 * Scroll-scrubbed video layer.
 *
 * The master is encoded with every frame as a keyframe, so `currentTime` seeks
 * land exactly in both directions.
 *
 * Seeking is asynchronous: assigning `currentTime` while a previous seek is
 * still resolving gets coalesced or dropped by the browser. Scroll produces far
 * more targets than the decoder can service, so we keep at most one seek in
 * flight and always chase the latest target when it completes. Without this the
 * element can strand mid-seek and stop responding — which shows up first when
 * scrolling backwards, because reverse motion tends to arrive as a dense burst
 * of decreasing targets.
 */
export const IntroFilm = forwardRef<IntroFilmHandle, IntroFilmProps>(function IntroFilm(
  { onReady },
  ref,
) {
  const video = useRef<HTMLVideoElement>(null);
  /** Latest position scroll has asked for, in seconds. */
  const wanted = useRef(0);
  /** Position of the seek currently in flight, or null when idle. */
  const inFlight = useRef<number | null>(null);
  const [poster, setPoster] = useState(true);

  const flush = useCallback(() => {
    const element = video.current;
    if (!element) return;
    // A seek is already resolving; `seeked`/`timeupdate` will chase the latest.
    if (inFlight.current !== null) return;
    // Seeks before metadata silently no-op, so wait for a real duration.
    if (!Number.isFinite(element.duration) || element.duration <= 0) return;

    const target = wanted.current;
    // Sub-frame moves are invisible and cost a decode.
    if (Math.abs(target - element.currentTime) < FRAME * 0.5) return;

    inFlight.current = target;
    try {
      element.currentTime = target;
    } catch {
      inFlight.current = null;
    }
  }, []);

  const setTravel = useCallback(
    (progress: number) => {
      const clamped = Math.min(1, Math.max(0, progress));
      // Hold just shy of the final frame; seeking exactly to duration can park
      // some browsers on a blank frame.
      wanted.current = Math.min(clamped * FILM_DURATION, FILM_DURATION - FRAME);
      flush();
    },
    [flush],
  );

  useImperativeHandle(ref, () => ({ setTravel }), [setTravel]);

  useEffect(() => {
    const element = video.current;
    if (!element) return;

    const onSeeked = () => {
      inFlight.current = null;
      // Scroll almost certainly moved on while this seek resolved.
      flush();
    };

    // Safari can drop a `seeked` under rapid scrubbing; `timeupdate` and a
    // periodic sweep both act as a release valve so the element cannot strand.
    const sweep = window.setInterval(() => {
      if (inFlight.current !== null && !element.seeking) {
        inFlight.current = null;
        flush();
      }
    }, 200);

    const announce = () => {
      setPoster(false);
      onReady?.();
      flush();
    };

    element.addEventListener("seeked", onSeeked);
    element.addEventListener("timeupdate", onSeeked);
    if (element.readyState >= 2) announce();
    else element.addEventListener("loadeddata", announce, { once: true });

    return () => {
      element.removeEventListener("seeked", onSeeked);
      element.removeEventListener("timeupdate", onSeeked);
      element.removeEventListener("loadeddata", announce);
      window.clearInterval(sweep);
    };
  }, [flush, onReady]);

  return (
    <div className="intro-film">
      <video
        ref={video}
        className="intro-film-video"
        // `preload="auto"` matters: metadata-only leaves seeks unserviceable.
        preload="auto"
        muted
        playsInline
        // Never plays — every frame shown is the result of a seek.
        autoPlay={false}
        poster="/media/intro/intro-poster.jpg"
        aria-hidden="true"
        // `media` on <source> is not honoured for video in current browsers, so
        // the responsive pick happens here rather than via multiple sources.
        src={
          window.matchMedia("(min-width: 768px)").matches
            ? "/media/intro/intro-desktop.mp4"
            : "/media/intro/intro-mobile.mp4"
        }
      />
      {poster ? <div className="intro-film-poster" aria-hidden="true" /> : null}
    </div>
  );
});
