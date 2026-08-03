import { memo, useEffect, useId, useRef, useState, type ComponentProps, type ReactNode } from "react";
import {
  MotionConfig,
  motion,
  useScroll,
  useTransform,
  type MotionValue,
} from "motion/react";
import { ArrowRight } from "@phosphor-icons/react/ArrowRight";
import { CalendarBlank } from "@phosphor-icons/react/CalendarBlank";
import { CheckCircle } from "@phosphor-icons/react/CheckCircle";
import {
  courseContent,
  type OwnershipStep,
  type Session,
  type ToolContent,
  type ToolId,
} from "./courseContent";

type Tool = ToolContent & {
  logo: ReactNode;
};

const easing = [0.16, 1, 0.3, 1] as const;
type MotionDivStyle = ComponentProps<typeof motion.div>["style"];
type LogoProps = { size?: number };

const {
  courseMeta,
  deliverables,
  parentReasons,
  profile,
  reserveHref,
  safetyNotes,
  sections,
  sessions,
  ownershipSteps,
} = courseContent;

const tools: Tool[] = courseContent.tools.map((tool) => ({
  ...tool,
  logo: <ToolLogo id={tool.id} />,
}));

function ToolLogo({ id }: { id: ToolId }) {
  if (id === "notebooklm") {
    return <NotebookLMMark size={46} />;
  }

  if (id === "codex") {
    return <CodexMark size={46} />;
  }

  return <ClaudeCodeMark size={46} />;
}

function NotebookLMMark({ size = 46 }: LogoProps) {
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      fill="currentColor"
      height={size}
      viewBox="0 0 24 24"
      width={size}
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect fill="#fff" height="24" rx="5" width="24" />
      <path
        d="M11.999 3.14C5.372 3.14 0 8.588 0 15.312v5.828h2.212v-.58c0-2.728 2.178-4.938 4.866-4.938 2.688 0 4.866 2.21 4.866 4.937v.581h2.212v-.58c0-3.967-3.17-7.18-7.078-7.18a6.966 6.966 0 00-4.086 1.318C4.2 12.262 6.687 10.59 9.56 10.59c4.057 0 7.347 3.338 7.347 7.453v3.097h2.212v-3.097c0-5.355-4.28-9.698-9.56-9.698a9.438 9.438 0 00-6.217 2.332C4.984 7.528 8.244 5.383 12 5.383c5.406 0 9.788 4.446 9.788 9.93v5.827H24v-5.828C23.999 8.588 18.627 3.14 11.999 3.14z"
        fill="#111827"
      />
    </svg>
  );
}

function CodexMark({ size = 46 }: LogoProps) {
  const gradientId = useId();

  return (
    <svg
      aria-hidden="true"
      focusable="false"
      height={size}
      viewBox="0 0 24 24"
      width={size}
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M19.503 0H4.496A4.496 4.496 0 000 4.496v15.007A4.496 4.496 0 004.496 24h15.007A4.496 4.496 0 0024 19.503V4.496A4.496 4.496 0 0019.503 0z"
        fill="#fff"
      />
      <path
        d="M9.064 3.344a4.578 4.578 0 012.285-.312c1 .115 1.891.54 2.673 1.275.01.01.024.017.037.021a.09.09 0 00.043 0 4.55 4.55 0 013.046.275l.047.022.116.057a4.581 4.581 0 012.188 2.399c.209.51.313 1.041.315 1.595a4.24 4.24 0 01-.134 1.223.123.123 0 00.03.115c.594.607.988 1.33 1.183 2.17.289 1.425-.007 2.71-.887 3.854l-.136.166a4.548 4.548 0 01-2.201 1.388.123.123 0 00-.081.076c-.191.551-.383 1.023-.74 1.494-.9 1.187-2.222 1.846-3.711 1.838-1.187-.006-2.239-.44-3.157-1.302a.107.107 0 00-.105-.024c-.388.125-.78.143-1.204.138a4.441 4.441 0 01-1.945-.466 4.544 4.544 0 01-1.61-1.335c-.152-.202-.303-.392-.414-.617a5.81 5.81 0 01-.37-.961 4.582 4.582 0 01-.014-2.298.124.124 0 00.006-.056.085.085 0 00-.027-.048 4.467 4.467 0 01-1.034-1.651 3.896 3.896 0 01-.251-1.192 5.189 5.189 0 01.141-1.6c.337-1.112.982-1.985 1.933-2.618.212-.141.413-.251.601-.33.215-.089.43-.164.646-.227a.098.098 0 00.065-.066 4.51 4.51 0 01.829-1.615 4.535 4.535 0 011.837-1.388zm3.482 10.565a.637.637 0 000 1.272h3.636a.637.637 0 100-1.272h-3.636zM8.462 9.23a.637.637 0 00-1.106.631l1.272 2.224-1.266 2.136a.636.636 0 101.095.649l1.454-2.455a.636.636 0 00.005-.64L8.462 9.23z"
        fill={`url(#${gradientId})`}
      />
      <defs>
        <linearGradient gradientUnits="userSpaceOnUse" id={gradientId} x1="12" x2="12" y1="3" y2="21">
          <stop stopColor="#B1A7FF" />
          <stop offset=".5" stopColor="#7A9DFF" />
          <stop offset="1" stopColor="#3941FF" />
        </linearGradient>
      </defs>
    </svg>
  );
}

function ClaudeCodeMark({ size = 46 }: LogoProps) {
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      height={size}
      viewBox="0 0 24 24"
      width={size}
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        clipRule="evenodd"
        d="M20.998 10.949H24v3.102h-3v3.028h-1.487V20H18v-2.921h-1.487V20H15v-2.921H9V20H7.488v-2.921H6V20H4.487v-2.921H3V14.05H0V10.95h3V5h17.998v5.949zM6 10.949h1.488V8.102H6v2.847zm10.51 0H18V8.102h-1.49v2.847z"
        fill="#D97757"
        fillRule="evenodd"
      />
    </svg>
  );
}

function getMotionOverride() {
  if (typeof window === "undefined") {
    return null;
  }

  return new URLSearchParams(window.location.search).get("motion");
}

function useMotionDisabled() {
  const mode = getMotionOverride();

  return mode === "reduce";
}

function useReducedMotionSetting() {
  return getMotionOverride() === "reduce" ? "always" : "never";
}

function useDesktopScrub() {
  const query = "(min-width: 981px)";
  const [canScrub, setCanScrub] = useState(() =>
    typeof window === "undefined" ? true : window.matchMedia(query).matches,
  );

  useEffect(() => {
    const mediaQuery = window.matchMedia(query);
    const update = () => setCanScrub(mediaQuery.matches);

    update();
    mediaQuery.addEventListener("change", update);
    return () => mediaQuery.removeEventListener("change", update);
  }, []);

  return canScrub;
}

function ScrollProgress() {
  const { scrollYProgress } = useScroll();

  return <motion.div className="scroll-progress" style={{ scaleY: scrollYProgress }} />;
}

function Reveal({
  children,
  className,
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) {
  const reduce = useMotionDisabled();

  return (
    <motion.div
      className={className}
      initial={reduce ? false : { opacity: 0, y: 28, scale: 0.99 }}
      whileInView={{ opacity: 1, scale: 1, y: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: 0.36, delay, ease: easing }}
    >
      {children}
    </motion.div>
  );
}

const CredentialLine = memo(function CredentialLine({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <span className="credential-line">
      <small>{label}</small>
      <strong>{value}</strong>
    </span>
  );
});

const DateTile = memo(function DateTile({ session }: { session: Session }) {
  return (
    <div className="date-tile">
      <CalendarBlank size={21} weight="duotone" aria-hidden="true" />
      <span>{session.title}</span>
      <strong>{session.date}</strong>
      <p>{session.outcome}</p>
    </div>
  );
});

function IntroFlow() {
  const reduce = useMotionDisabled();
  const canScrub = useDesktopScrub();

  if (reduce || !canScrub) {
    return <IntroFlowStatic />;
  }

  return <IntroFlowScrubbed />;
}

function IntroProfileContent({
  reduce,
  entrance = true,
}: {
  reduce: boolean;
  entrance?: boolean;
}) {
  const shouldAnimateIn = !reduce && entrance;

  return (
    <>
      <motion.p
        className="eyebrow"
        initial={shouldAnimateIn ? { opacity: 0, y: 16 } : false}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.32, ease: easing }}
      >
        {profile.eyebrow}
      </motion.p>
      <motion.h1
        id="profile-title"
        initial={shouldAnimateIn ? { opacity: 0, y: 24 } : false}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.38, delay: 0.02, ease: easing }}
      >
        {profile.name}
      </motion.h1>
      <motion.div
        className="hero__credentials"
        initial={shouldAnimateIn ? { opacity: 0, y: 18 } : false}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.34, delay: 0.05, ease: easing }}
      >
        {profile.credentials.map((credential) => (
          <CredentialLine
            key={credential.value}
            label={credential.label}
            value={credential.value}
          />
        ))}
      </motion.div>
      <motion.p
        className="hero__lede"
        initial={shouldAnimateIn ? { opacity: 0, y: 18 } : false}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.34, delay: 0.08, ease: easing }}
      >
        {profile.lede}
      </motion.p>
    </>
  );
}

function ReasonContent() {
  return (
    <>
      <p className="eyebrow">{sections.reason.eyebrow}</p>
      <h2>{sections.reason.title}</h2>
      <p>{sections.reason.body}</p>
      <div className="reason-strip" aria-label="Why students need this now">
        {parentReasons.map((reason) => (
          <article key={reason.title}>
            <span>{reason.tag}</span>
            <strong>{reason.title}</strong>
            <p>{reason.body}</p>
          </article>
        ))}
      </div>
    </>
  );
}

function IntroFlowStatic() {
  const reduce = useMotionDisabled();

  return (
    <section className="intro-flow intro-flow--static" aria-labelledby="profile-title">
      <div className="intro-flow__sticky">
        <Reveal className="intro-flow__profile">
          <IntroProfileContent reduce={reduce} />
        </Reveal>
        <Reveal className="journey-artifact" delay={0.05}>
          <CourseDossierStatic />
        </Reveal>
        <Reveal className="intro-flow__reason" delay={0.08}>
          <ReasonContent />
        </Reveal>
      </div>
    </section>
  );
}

function IntroFlowScrubbed() {
  const ref = useRef<HTMLElement>(null);
  const reduce = useMotionDisabled();
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end end"],
  });
  const handoff = useTransform(scrollYProgress, [0.22, 0.68], [0, 1]);

  const profileOpacity = useTransform(handoff, [0, 0.34, 0.72, 1], [1, 0.86, 0, 0]);
  const profileY = useTransform(handoff, [0, 1], [0, -88]);
  const profileScale = useTransform(handoff, [0, 1], [1, 0.965]);

  const reasonOpacity = useTransform(handoff, [0, 0.48, 0.86, 1], [0, 0, 1, 1]);
  const reasonY = useTransform(handoff, [0, 1], [58, -24]);
  const reasonScale = useTransform(handoff, [0, 1], [0.982, 1]);

  return (
    <section className="intro-flow intro-flow--scrubbed" ref={ref} aria-labelledby="profile-title">
      <div className="intro-flow__sticky">
        <motion.div
          className="intro-flow__profile"
          style={{ opacity: profileOpacity, scale: profileScale, y: profileY }}
        >
          <IntroProfileContent reduce={reduce} entrance={false} />
        </motion.div>

        <JourneyArtifact handoff={handoff} reduce={reduce} />

        <motion.div
          className="intro-flow__reason"
          style={{ opacity: reasonOpacity, scale: reasonScale, y: reasonY }}
        >
          <ReasonContent />
        </motion.div>
      </div>
    </section>
  );
}

function JourneyArtifact({ handoff, reduce }: { handoff: MotionValue<number>; reduce: boolean }) {
  const courseOpacity = useTransform(handoff, [0, 0.44, 0.76, 1], [1, 0.95, 0, 0]);
  const courseY = useTransform(handoff, [0, 1], [0, -20]);
  const loopOpacity = useTransform(handoff, [0, 0.52, 0.84, 1], [0, 0, 1, 1]);
  const loopY = useTransform(handoff, [0, 1], [42, 0]);
  const beamScale = useTransform(handoff, [0.6, 0.96, 1], [0.08, 1, 1]);

  return (
    <motion.div
      className="journey-artifact"
      initial={reduce ? false : { opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.42, delay: 0.04, ease: easing }}
    >
      <div className="artifact-shell">
        <DossierHeader />
        <DossierCourseLayer style={reduce ? undefined : { opacity: courseOpacity, y: courseY }} />

        <motion.div className="artifact-loop" style={reduce ? undefined : { opacity: loopOpacity, y: loopY }}>
          <div className="artifact-loop__header">
            <span>{sections.dossier.habitsKicker}</span>
            <strong>{sections.dossier.habitsTitle}</strong>
          </div>
          <div className="loop-track">
            <motion.span className="loop-track__beam" style={reduce ? undefined : { scaleX: beamScale }} />
            {ownershipSteps.map((step, index) => (
              <LoopStep index={index} key={step.verb} step={step} />
            ))}
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
}

function CourseDossierStatic() {
  return (
    <div className="artifact-shell">
      <DossierHeader />
      <DossierCourseLayer />
      <div className="artifact-loop artifact-loop--static">
        <div className="artifact-loop__header">
          <span>{sections.dossier.habitsKicker}</span>
          <strong>{sections.dossier.habitsTitle}</strong>
        </div>
        <div className="loop-track">
          <span className="loop-track__beam" />
          {ownershipSteps.map((step, index) => (
            <StaticLoopStep index={index} key={step.verb} step={step} />
          ))}
        </div>
      </div>
    </div>
  );
}

function DossierHeader() {
  return (
    <div className="artifact-header">
      <span>{sections.dossier.kicker}</span>
      <strong>{sections.dossier.title}</strong>
    </div>
  );
}

function DossierCourseLayer({ style }: { style?: MotionDivStyle }) {
  return (
    <motion.div className="artifact-course" style={style}>
      <div className="artifact-course__top">
        <span>Dates</span>
        <strong>{sections.dossier.dates}</strong>
      </div>
      <div className="artifact-course__meta" aria-label="Course details">
        {courseMeta.map((item) => (
          <span key={item.label}>
            <small>{item.label}</small>
            <strong>{item.value}</strong>
          </span>
        ))}
      </div>
      <p className="artifact-safety">{sections.dossier.safety}</p>
      <div className="artifact-session-grid">
        {sessions.map((session) => (
          <div key={session.date}>
            <span>{session.date}</span>
            <strong>{session.title}</strong>
            <p>{session.focus}</p>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

function LoopStep({ step, index }: { step: OwnershipStep; index: number }) {
  return (
    <div className="loop-step">
      <span>{index + 1}</span>
      <strong>{step.verb}</strong>
      <p>{step.detail}</p>
    </div>
  );
}

function StaticLoopStep({ step, index }: { step: OwnershipStep; index: number }) {
  return (
    <div className="loop-step">
      <span>{index + 1}</span>
      <strong>{step.verb}</strong>
      <p>{step.detail}</p>
    </div>
  );
}

function ToolsSection() {
  const [activeToolId, setActiveToolId] = useState<ToolId>(tools[0].id);
  const activeTool = tools.find((tool) => tool.id === activeToolId) ?? tools[0];

  return (
    <section className="tools-section" aria-labelledby="tools-title">
      <Reveal className="section-copy">
        <h2 id="tools-title">{sections.tools.title}</h2>
        <p>{sections.tools.body}</p>
      </Reveal>
      <Reveal className="tool-console" delay={0.06}>
        <div className="tool-tabs" role="tablist" aria-label="AI tools practiced in the class">
          {tools.map((tool) => (
            <button
              aria-controls="tool-panel"
              aria-selected={tool.id === activeTool.id}
              className="tool-tab"
              id={`tool-tab-${tool.id}`}
              key={tool.id}
              onClick={() => setActiveToolId(tool.id)}
              role="tab"
              type="button"
            >
              <span aria-hidden="true">{tool.logo}</span>
              {tool.name}
            </button>
          ))}
        </div>
        <motion.article
          animate={{ opacity: 1, y: 0 }}
          aria-labelledby={`tool-tab-${activeTool.id}`}
          className="tool-panel"
          id="tool-panel"
          initial={{ opacity: 0, y: 8 }}
          key={activeTool.id}
          role="tabpanel"
          transition={{ duration: 0.22, ease: easing }}
        >
          <div className="tool-panel__identity">
            <span className="tool-panel__logo">{activeTool.logo}</span>
            <div>
              <h3>{activeTool.name}</h3>
              <p>{activeTool.label}</p>
            </div>
          </div>
          <p className="tool-panel__body">{activeTool.body}</p>
          <div className="tool-panel__chips" aria-label={`${activeTool.name} teaching focus`}>
            {activeTool.teaches.map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
        </motion.article>
      </Reveal>
    </section>
  );
}

function CoursePlanSection() {
  return (
    <section className="course-plan" aria-labelledby="course-title">
      <Reveal className="section-copy section-copy--center">
        <h2 id="course-title">{sections.plan.title}</h2>
        <p>{sections.plan.body}</p>
      </Reveal>
      <div className="course-plan__grid">
        {sessions.map((session, index) => (
          <Reveal delay={index * 0.08} key={session.date}>
            <article className="session-card">
              <div className="session-card__date">
                <span>{session.title}</span>
                <strong>{session.date}</strong>
              </div>
              <p>{session.focus}</p>
              <div>
                <CheckCircle size={18} weight="fill" aria-hidden="true" />
                {session.outcome}
              </div>
            </article>
          </Reveal>
        ))}
      </div>
      <Reveal className="receipt-panel" delay={0.08}>
        <div>
          <span className="receipt-mark" aria-hidden="true">
            {sections.receipt.mark}
          </span>
          <h3>{sections.receipt.title}</h3>
          <p>{sections.receipt.body}</p>
        </div>
        <div className="deliverable-list" aria-label="Student deliverables">
          {deliverables.map((item) => (
            <span key={item}>{item}</span>
          ))}
        </div>
      </Reveal>
    </section>
  );
}

function ContactSection() {
  return (
    <section className="contact-section" aria-labelledby="contact-title">
      <Reveal className="contact-panel">
        <div>
          <span className="contact__mark">{sections.contact.mark}</span>
          <h2 id="contact-title">{sections.contact.title}</h2>
          <p>{sections.contact.body}</p>
          <a
            className="primary-cta"
            href={reserveHref}
          >
            {sections.contact.cta}
            <ArrowRight size={18} weight="bold" aria-hidden="true" />
          </a>
        </div>
        <div>
          <div className="contact__dates">
            {sessions.map((session) => (
              <DateTile key={session.date} session={session} />
            ))}
          </div>
          <div className="safety-strip" aria-label="Safety and responsibility notes">
            {safetyNotes.map((note) => (
              <span key={note}>{note}</span>
            ))}
          </div>
        </div>
      </Reveal>
    </section>
  );
}

export default function App() {
  const reducedMotion = useReducedMotionSetting();

  return (
    <MotionConfig reducedMotion={reducedMotion} transition={{ ease: easing }}>
      <ScrollProgress />
      <main>
        <IntroFlow />
        <ToolsSection />
        <CoursePlanSection />
        <ContactSection />
      </main>
    </MotionConfig>
  );
}
