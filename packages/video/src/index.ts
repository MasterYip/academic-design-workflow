export type VideoTheme = {
  width: number;
  height: number;
  fps: number;
  safe_area_percent: number;
  title_duration_s: number;
  transition: string;
};

export type Scene = { id: string; claim: string; durationSeconds: number };
export type TimedScene = Scene & { fromFrame: number; durationFrames: number };

export function safeArea(theme: VideoTheme) {
  const x = theme.width * theme.safe_area_percent / 100;
  const y = theme.height * theme.safe_area_percent / 100;
  return { x, y, width: theme.width - 2 * x, height: theme.height - 2 * y };
}

export function buildTimeline(theme: VideoTheme, scenes: Scene[]): TimedScene[] {
  let frame = 0;
  return scenes.map((scene) => {
    const durationFrames = Math.max(1, Math.round(scene.durationSeconds * theme.fps));
    const timed = { ...scene, fromFrame: frame, durationFrames };
    frame += durationFrames;
    return timed;
  });
}

