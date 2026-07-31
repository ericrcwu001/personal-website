import { ArrowUpRight } from "@phosphor-icons/react";
import { projects } from "../data/projects";

export function ProjectChooser() {
  return (
    <section className="projects-section" id="projects" aria-labelledby="projects-title">
      <header className="projects-heading">
        <h2 id="projects-title">Projects</h2>
        <p>AI systems I've built across research, evaluation, and product.</p>
      </header>

      <div className="project-list">
        {projects.map((project) => (
          <a className="project-link" href={`/projects/${project.slug}`} key={project.slug}>
            <span>{project.title}</span>
            <ArrowUpRight aria-hidden="true" />
          </a>
        ))}
      </div>
    </section>
  );
}
