export type ProjectSection = {
  id: string;
  eyebrow?: string;
  title: string;
  summary?: string;
};

export function renderSectionHeading(section: ProjectSection): string {
  const eyebrow = section.eyebrow
    ? `<p class="adw-eyebrow">${section.eyebrow}</p>`
    : "";
  const summary = section.summary
    ? `<p class="adw-section-summary">${section.summary}</p>`
    : "";
  return `<header class="adw-section-heading" id="${section.id}">${eyebrow}<h2>${section.title}</h2>${summary}</header>`;
}

