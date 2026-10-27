"""Generate the profile dashboard from GitHub data; no third-party packages."""
from datetime import datetime, timezone
from html import escape
from pathlib import Path
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OWNER = "otaviorodriguess"
START = "<!-- PROFILE:START -->"
END = "<!-- PROFILE:END -->"

def api(*args):
    result = subprocess.run(
        ["gh", "api", *args], check=True, capture_output=True,
        encoding="utf-8", timeout=90,
    )
    return json.loads(result.stdout)

def svg(body, width, height, label):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(label)}">'
        '<style>@media(prefers-reduced-motion:reduce){.pulse{display:none}}</style>'
        f'<rect x="1" y="1" width="{width-2}" height="{height-2}" rx="18" '
        'fill="#16121f" stroke="#3a2e4b"/>'
        '<g font-family="Segoe UI,Arial,sans-serif">'
        + body + '</g></svg>\n'
    )

def main():
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks { contributionDays { date contributionCount weekday contributionLevel } }
          }
        }
      }
    }
    """
    response = api("graphql", "-f", "query=" + query, "-f", "login=" + OWNER)
    if response.get("errors"):
        raise RuntimeError("GitHub rejected contribution query")
    calendar = response["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    pages = api("--paginate", "--slurp", f"users/{OWNER}/repos?type=owner&per_page=100")
    repos = [r for page in pages for r in page if not r["private"]]
    originals = [r for r in repos if not r["fork"] and not r["archived"]]
    stars = sum(r["stargazers_count"] for r in repos)
    languages = sorted({r["language"] for r in originals if r["language"]})
    stamp = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    values = [
        (str(calendar["totalContributions"]), "CONTRIBUIÇÕES", "últimos 12 meses"),
        (str(len(originals)), "PROJETOS", "públicos · próprios · ativos"),
        (str(len(languages)), "LINGUAGENS", "principais dos projetos"),
        (str(stars), "ESTRELAS", "nos repositórios públicos"),
    ]
    body = '<text x="30" y="33" font-size="11" letter-spacing="2.5" fill="#c4b5fd">CÓDIGO EM MOVIMENTO</text>'
    for i, (number, label, note) in enumerate(values):
        x = 30 + i * 270
        if i:
            body += f'<path d="M{x-18} 58v94" stroke="#392d48"/>'
        body += (
            f'<text x="{x}" y="99" font-size="43" font-weight="700" fill="#f5efff">{number}</text>'
            f'<text x="{x}" y="127" font-size="11" letter-spacing="1.5" fill="#c4b5fd">{label}</text>'
            f'<text x="{x}" y="151" font-size="12" fill="#b5a8c6">{note}</text>'
        )
    body += f'<text x="30" y="189" font-size="11" fill="#9c8bae">Dados do GitHub · atualizado em {stamp} UTC</text>'
    stats = svg(body, 1140, 210, "Estatísticas reais de Otávio Rodrigues no GitHub")

    colors = {
        "NONE": "#241d31", "FIRST_QUARTILE": "#51406a",
        "SECOND_QUARTILE": "#795a9d", "THIRD_QUARTILE": "#a580d0",
        "FOURTH_QUARTILE": "#d8b4fe",
    }
    weeks = calendar["weeks"]
    grid = (
        '<text x="30" y="37" font-size="12" letter-spacing="2" fill="#c4b5fd">UM DIA DE CADA VEZ</text>'
        '<text x="30" y="67" font-size="23" font-weight="650" fill="#f5efff">Pequenos passos. Código em evolução.</text>'
    )
    for col, week in enumerate(weeks):
        for day in week["contributionDays"]:
            x, y = 30 + col * 20, 96 + day["weekday"] * 20
            title = f'{day["date"]}: {day["contributionCount"]} contribuições'
            grid += (
                f'<rect x="{x}" y="{y}" width="15" height="15" rx="4" '
                f'fill="{colors[day["contributionLevel"]]}"><title>{title}</title></rect>'
            )
    grid += '<text x="30" y="272" font-size="12" fill="#b5a8c6">Cada quadrado representa um dia · últimos 12 meses</text>'
    for i, color in enumerate(colors.values()):
        grid += f'<rect x="{946+i*23}" y="255" width="15" height="15" rx="4" fill="{color}"/>'
    grid += (
        '<circle class="pulse" cx="1093" cy="32" r="5" fill="#d8b4fe">'
        '<animate attributeName="opacity" values=".3;1;.3" dur="3s" repeatCount="indefinite"/>'
        '</circle>'
    )
    graph = svg(grid, 1140, 300, "Calendário real de contribuições dos últimos 12 meses")

    recent = sorted(
        [r for r in originals if r["name"] != OWNER and r.get("pushed_at")],
        key=lambda r: r["pushed_at"], reverse=True,
    )[:4]
    lines = [
        '<img src="./assets/profile-stats.svg" width="100%" alt="Contribuições, projetos públicos ativos, linguagens e estrelas de Otávio no GitHub" />',
        "",
        '<details>',
        '<summary><b>↳ Projetos movimentados recentemente</b></summary>',
        "",
        "| Projeto | Linguagem principal | Último push (UTC) |",
        "| :--- | :--- | :--- |",
    ]
    for repo in recent:
        name = re.sub(r"([\\[\\]_*|])", r"\\\1", repo["name"])
        language = repo["language"] or "—"
        pushed = datetime.fromisoformat(repo["pushed_at"].replace("Z", "+00:00")).strftime("%d/%m/%Y")
        lines.append(f'| [{name} ↗]({repo["html_url"]}) | {language} | {pushed} |')
    lines.extend([
        "", "</details>", "", "<br />", "",
        '<a href="https://github.com/otaviorodriguess?tab=overview"><img src="./assets/contribution-calendar.svg" width="100%" alt="Calendário de contribuições de Otávio: cada quadrado representa um dia dos últimos 12 meses" /></a>',
        "",
        '<sub>Este painel se atualiza diariamente com GitHub Actions. As linguagens representam a linguagem principal de cada projeto, sem classificação de domínio.</sub>',
    ])
    readme_path = ROOT / "README.md"
    text = readme_path.read_text(encoding="utf-8")
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError("README must contain exactly one dashboard marker pair")
    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    updated = before + START + "\n" + "\n".join(lines) + "\n" + END + after
    # Complete all reads and validation before replacing any tracked content.
    (ROOT / "assets").mkdir(exist_ok=True)
    (ROOT / "assets/profile-stats.svg").write_text(stats, encoding="utf-8")
    (ROOT / "assets/contribution-calendar.svg").write_text(graph, encoding="utf-8")
    readme_path.write_text(updated, encoding="utf-8")
    print("Dashboard generated from GitHub: statistics, contribution calendar and recent projects.")

if __name__ == "__main__":
    main()

