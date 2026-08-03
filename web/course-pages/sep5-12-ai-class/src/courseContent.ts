export type ToolId = "notebooklm" | "codex" | "claude-code";

export type Session = {
  date: string;
  title: string;
  focus: string;
  outcome: string;
};

export type OwnershipStep = {
  verb: string;
  detail: string;
};

export type ToolContent = {
  id: ToolId;
  name: string;
  label: string;
  body: string;
  teaches: string[];
};

export const courseContent = {
  reserveHref:
    "mailto:?subject=Reserve%20a%20seat%20for%20Eric%20Wu%27s%204-hour%20AI%20course",
  profile: {
    eyebrow: "Instructor",
    name: "Eric Wu",
    credentials: [
      { label: "Stanford", value: "Stanford '29 CS and Math" },
      { label: "Hong Kong", value: "Chinese International School IB 44" },
    ],
    lede:
      "A compact course for students who are already going to use AI. The goal is to help them learn from it, question it, and build with it without handing over their thinking.",
  },
  courseMeta: [
    { label: "Course", value: "4-hour course" },
    { label: "Audience", value: "Grades 8 and up" },
    { label: "Dates", value: "Sep 5 and Sep 12" },
    { label: "Experience", value: "No coding required" },
  ],
  sessions: [
    {
      date: "Sep 5",
      title: "Understand",
      focus:
        "Use NotebookLM with approved sources, citations, skeptical questions, and a teach-back artifact.",
      outcome: "A checked study guide, quiz, or source-backed learning artifact.",
    },
    {
      date: "Sep 12",
      title: "Build",
      focus:
        "Turn verified notes into a clear brief, then supervise Codex as it builds and tests a one-screen prototype.",
      outcome: "A small prototype plus test notes and one revised or rejected AI suggestion.",
    },
  ] satisfies Session[],
  ownershipSteps: [
    { verb: "Think", detail: "start with the goal" },
    { verb: "Direct", detail: "give context and limits" },
    { verb: "Check", detail: "open sources and tests" },
    { verb: "Improve", detail: "revise with judgment" },
    { verb: "Explain", detail: "own the final answer" },
  ] satisfies OwnershipStep[],
  parentReasons: [
    {
      tag: "Now",
      title: "AI is already in the homework loop.",
      body:
        "By 8th grade, students can reach tools that sound confident, cite sources, and write code.",
    },
    {
      tag: "Edge",
      title: "Judgment matters more than prompt tricks.",
      body:
        "The durable skill is knowing what to ask, what context to provide, and when an answer is weak.",
    },
    {
      tag: "Guardrail",
      title: "Agents raise the stakes.",
      body:
        "When AI can change files and run commands, students need boundaries, tests, and responsibility.",
    },
  ],
  tools: [
    {
      id: "notebooklm",
      name: "NotebookLM",
      label: "source-backed learning",
      body:
        "Students build from approved source packs, open citations, compare evidence, and make a study artifact they can explain.",
      teaches: ["trusted sources", "citation checks", "teach-back"],
    },
    {
      id: "codex",
      name: "Codex",
      label: "agent-directed building",
      body:
        "Students turn verified notes into a clear brief, supervise a small build, run checks, and inspect what changed.",
      teaches: ["clear brief", "one-screen build", "test record"],
    },
    {
      id: "claude-code",
      name: "Claude Code",
      label: "workflow comparison",
      body:
        "Eric demos Claude Code as a comparison tool so students see permissions, scope, review, and agent boundaries.",
      teaches: ["permissions", "scope", "review"],
    },
  ] satisfies ToolContent[],
  deliverables: [
    "NotebookLM study artifact",
    "source check",
    "Codex prototype",
    "test notes",
    "revised or rejected AI suggestion",
  ],
  safetyNotes: [
    "approved source packs",
    "no private student data",
    "no APIs or deployment",
    "Claude Code instructor demo",
    "students explain final work",
  ],
  sections: {
    dossier: {
      kicker: "Course plan",
      title: "Learn smarter. Build carefully.",
      dates: "Sep 5 + Sep 12",
      safety:
        "Supervised and age-appropriate: approved sources, no private student data, no APIs, no public deployment.",
      habitsKicker: "Five habits",
      habitsTitle: "Brain before bot. Check before trust.",
    },
    reason: {
      eyebrow: "Why this matters",
      title: "The point is not faster copying. It is making students harder to fool.",
      body:
        "Students need a repeatable way to choose trusted context, question confident answers, test AI-made work, and explain the final decision.",
    },
    tools: {
      title: "What students will actually practice.",
      body:
        "A short, real-tool workflow: learn from sources in NotebookLM, turn verified notes into a brief, supervise Codex on a small build, then compare Claude Code as an instructor demo.",
    },
    plan: {
      title: "Two Saturdays. Four hours. Tangible work.",
      body:
        "Session 1 teaches students to learn from sources, not just answers. Session 2 turns that thinking into a checkable prototype.",
    },
    receipt: {
      mark: "checked",
      title: "They leave with work they can defend.",
      body:
        "A checked study artifact, a small prototype, test notes, and a record of what they verified or changed.",
    },
    closing: {
      mark: "Sep 5 + Sep 12",
      title: "The outcome is confidence with responsibility.",
      body:
        "Students leave with a practical loop for using AI: define the goal, provide trusted context, check the work, improve it, and explain it.",
      cta: "Reserve a seat",
    },
  },
} as const;
