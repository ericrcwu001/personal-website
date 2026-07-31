import { CinematicIntro } from "./components/CinematicIntro";
import { ProjectChooser } from "./components/ProjectChooser";
import { ProjectPlaceholder } from "./components/ProjectPlaceholder";
import { SiteNav } from "./components/SiteNav";

function Home() {
  return (
    <main>
      <SiteNav />
      <CinematicIntro />
      <ProjectChooser />
      <footer className="site-footer">
        <span>Eric Wu</span>
        <a href="mailto:ericrcwu@stanford.edu">ericrcwu@stanford.edu</a>
      </footer>
    </main>
  );
}

export default function App() {
  const projectMatch = window.location.pathname.match(/^\/projects\/([^/]+)\/?$/);
  if (projectMatch) return <ProjectPlaceholder slug={projectMatch[1]} />;
  return <Home />;
}
