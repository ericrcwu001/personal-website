import { ArrowLeft } from "@phosphor-icons/react";
import { projects } from "../data/projects";
import { SiteNav } from "./SiteNav";

export function ProjectPlaceholder({ slug }: { slug: string }) {
  const project = projects.find((candidate) => candidate.slug === slug);

  return (
    <main className="project-page">
      <SiteNav />
      <div className="project-page-content">
        <a className="back-link" href="/#projects">
          <ArrowLeft aria-hidden="true" />
          Projects
        </a>
        <h1>{project?.title ?? "Project"}</h1>
        <p>The case study and interactive showcase are being prepared.</p>
      </div>
    </main>
  );
}
