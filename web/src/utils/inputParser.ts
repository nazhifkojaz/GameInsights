export type ParsedInput =
  | { type: "appid"; appid: string }
  | { type: "name"; query: string };

const STEAM_URL_REGEX = /store\.steampowered\.com\/app\/(\d+)/;

export function parseSearchInput(input: string): ParsedInput {
  const trimmed = input.trim();

  // Check for Steam URL
  const urlMatch = trimmed.match(STEAM_URL_REGEX);
  if (urlMatch) {
    return { type: "appid", appid: urlMatch[1] };
  }

  // Check for numeric AppID
  if (/^\d+$/.test(trimmed)) {
    return { type: "appid", appid: trimmed };
  }

  // Default: treat as game name search
  return { type: "name", query: trimmed };
}
