import { useCallback, useLayoutEffect, useRef, useState } from "react";
import {
  EnvelopeSimple,
  GithubLogo,
  InstagramLogo,
  LinkedinLogo,
  XLogo,
} from "@phosphor-icons/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { IntroFilm, type IntroFilmHandle } from "./IntroFilm";

gsap.registerPlugin(ScrollTrigger);

/**
 * Beat map, as normalized progress through the 29s master.
 *
 * These are measured off the assembled footage, not chosen freely — each copy
 * treatment has to land while the camera is actually doing the thing that beat
 * describes. Re-derive these if the master is re-cut.
 */
const FILM = {
  /** wide panorama, camera barely drifting — the opening title sits here */
  openHold: 0.055,
  /** push toward Two IFC / Bank of China Tower */
  pushEnd: 0.167,
  /** crane: skyline exits through the lower edge */
  craneEnd: 0.276,
  /** above the cloud deck — no landmark pixels, no copy */
  apexEnd: 0.444,
  /** descent through cloud toward campus */
  descentEnd: 0.583,
  /** church legible on screen — verified against the footage, not the cut point */
  churchArrive: 0.6,
  /** church held — the Stanford copy sits here */
  churchHoldEnd: 0.824,
  /** whip pan, heavy motion blur — cover for the copy swap */
  panEnd: 0.848,
} as const;

/**
 * Fraction of the runway spent after the film has finished.
 *
 * The film reaches its last frame at (1 - TAIL) and the remaining scroll holds
 * that frame, so the social links can't be flicked past by overscrolling — the
 * pin only releases once the veil has covered.
 */
const TAIL = 0.18;

export function CinematicIntro() {
  const root = useRef<HTMLElement>(null);
  const film = useRef<IntroFilmHandle>(null);
  const [ready, setReady] = useState(false);
  const handleReady = useCallback(() => setReady(true), []);

  useLayoutEffect(() => {
    if (!root.current || !ready) return;

    const mediaQuery = gsap.matchMedia();
    const context = gsap.context(() => {
      // "all": the film runs for every visitor, including those with reduced
      // motion set. Deliberate — there is no reduced-motion intro variant.
      mediaQuery.add("all", () => {
        film.current?.setTravel(0);
        gsap.set(".work-veil", { yPercent: 102 });
        gsap.set(".identity-interests .interests-kicker, .identity-interests .interest", {
          clipPath: "inset(0 100% 0 0)",
        });
        // Stanford's two lines animate individually, each rising into its own
        // clip box, so the reveal tracks the glyphs rather than the 100dvh
        // wrapper.
        gsap.set(".identity-stanford", { autoAlpha: 1 });
        gsap.set(".identity-stanford h2, .identity-stanford p", {
          clipPath: "inset(105% 0 -5% 0)",
          yPercent: 18,
        });
        // Icons animate per-icon; clipping the flex row would crawl the gaps.
        gsap.set(".social-links", { autoAlpha: 1, clipPath: "none" });
        gsap.set(".social-links a", { autoAlpha: 0, yPercent: 34, scale: 0.92 });

        // One tween drives the film linearly; copy beats are positioned against
        // the same timeline so film and text cannot drift apart.
        const travel = { value: 0 };
        const timeline = gsap.timeline({
          defaults: { ease: "none" },
          scrollTrigger: {
            trigger: root.current,
            start: "top top",
            end: "bottom bottom",
            scrub: 0.65,
            invalidateOnRefresh: true,
          },
        });

        // Film runs over the first (1 - TAIL) of the timeline; the remainder
        // holds the final frame so the links get real dwell time.
        const play = 1 - TAIL;
        /** Convert a film-relative position (0..1) to a timeline position. */
        const at = (filmProgress: number) => filmProgress * play;

        timeline.to(
          travel,
          {
            value: 1,
            duration: play,
            onUpdate: () => film.current?.setTravel(travel.value),
          },
          0,
        );

        timeline
          // `Eric Wu` holds across the opening drift and most of the push.
          .to(".identity-name", { clipPath: "inset(0 0 100% 0)", duration: 0.022 }, at(0.105))
          // Interests accumulate through the rest of the push and into the
          // start of the crane, while the skyline is still readable.
          .to(".identity-interests", { autoAlpha: 1, duration: 0.002 }, at(0.132))
          .to(".interests-kicker", { clipPath: "inset(0 0% 0 0)", duration: 0.016 }, at(0.134))
          .to(".interest-1", { clipPath: "inset(0 0% 0 0)", duration: 0.024 }, at(0.16))
          .to(".interest-2", { clipPath: "inset(0 0% 0 0)", duration: 0.024 }, at(0.192))
          .to(".interest-3", { clipPath: "inset(0 0% 0 0)", duration: 0.024 }, at(0.224))
          .to(".interest-4", { clipPath: "inset(0 0% 0 0)", duration: 0.024 }, at(0.256))
          // Retire the list once the city has dropped away below frame.
          .to(".identity-interests", { yPercent: 24, autoAlpha: 0, duration: 0.03 }, at(0.33))
          // Apex is deliberately copy-free: nothing between craneEnd and descentEnd.
          // `Stanford` rises line by line once the church is settled on screen.
          .to(
            ".identity-stanford h2, .identity-stanford p",
            {
              clipPath: "inset(-5% 0 -5% 0)",
              yPercent: 0,
              duration: 0.042,
              ease: "power2.out",
              stagger: 0.018,
            },
            at(FILM.churchArrive),
          )
          // The whip pan's motion blur covers its retirement.
          .to(
            ".identity-stanford h2, .identity-stanford p",
            {
              clipPath: "inset(-5% 0 105% 0)",
              yPercent: -12,
              duration: 0.024,
              ease: "power2.in",
              stagger: 0.008,
            },
            at(FILM.churchHoldEnd),
          )
          // Icons arrive one after another as the arcade glide settles, then
          // hold through the tail on the film's final frame.
          .to(
            ".social-links a",
            {
              autoAlpha: 1,
              yPercent: 0,
              scale: 1,
              duration: 0.03,
              ease: "back.out(1.6)",
              stagger: 0.011,
            },
            at(FILM.panEnd + 0.012),
          )
          .to(
            ".social-links a",
            {
              autoAlpha: 0,
              yPercent: -18,
              duration: 0.022,
              ease: "power2.in",
              stagger: 0.006,
            },
            0.93,
          )
          // Column sweep hands off to Work at the very end of the runway.
          .to(".work-veil", { yPercent: 0, duration: 0.055 }, 0.94);

        return () => timeline.kill();
      });
    }, root);

    ScrollTrigger.refresh();
    return () => {
      mediaQuery.revert();
      context.revert();
    };
  }, [ready]);

  return (
    <section
      ref={root}
      className="cinematic-runway"
      aria-label="Identity introduction"
    >
      <div className="cinematic-stage">
        <div className={`scene-loader ${ready ? "is-ready" : ""}`} aria-live="polite">
          <span>Eric Wu</span>
          <small>{ready ? "" : "Preparing scene"}</small>
        </div>

        <div className="world-environment" aria-hidden="true">
          <IntroFilm ref={film} onReady={handleReady} />
        </div>

        <div className="identity identity-name">
          <h1>Eric Wu</h1>
          <p>Stanford '29, AI Engineer &amp; Researcher</p>
        </div>

        <div className="identity identity-interests" aria-label="Interests">
          <span className="interests-kicker">Interested in:</span>
          <p className="interest interest-1">AI Engineering &amp; Research</p>
          <p className="interest interest-2">Math</p>
          <p className="interest interest-3">CS</p>
          <p className="interest interest-4">Public Policy</p>
        </div>

        <div className="identity identity-stanford">
          <h2>Stanford</h2>
          <p>Class of 2029</p>
        </div>

        <div className="social-links" aria-label="Social links">
          <a href="https://github.com/ericrcwu001" target="_blank" rel="noreferrer" aria-label="GitHub">
            <GithubLogo weight="fill" />
          </a>
          <a href="https://linkedin.com/in/ericrcwu" target="_blank" rel="noreferrer" aria-label="LinkedIn">
            <LinkedinLogo weight="fill" />
          </a>
          <a href="https://x.com/ericrcwu17" target="_blank" rel="noreferrer" aria-label="X">
            <XLogo />
          </a>
          <a href="https://instagram.com/ericrcwu" target="_blank" rel="noreferrer" aria-label="Instagram">
            <InstagramLogo />
          </a>
          <a href="mailto:ericrcwu@stanford.edu" aria-label="Email">
            <EnvelopeSimple />
          </a>
        </div>

        <div className="work-veil" aria-hidden="true" />
      </div>
    </section>
  );
}
