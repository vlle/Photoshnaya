package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"time"
)

const (
	defaultDeployHost = "157.22.182.58"
	defaultDeployUser = "root"
	defaultDeployPort = "22"
)

const pageTemplate = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Deploy Setup Helper</title>
  <style>
    :root {
      --bg: #f4f1e8;
      --panel: #fffaf0;
      --accent: #0f5c4d;
      --accent-soft: #d9efe7;
      --text: #1f2a24;
      --muted: #58655d;
      --border: #d6d1c3;
      --warn: #8c5a11;
      --warn-soft: #f6e6cb;
      --code: #132019;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, "Iowan Old Style", serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, #efe2c2 0, transparent 34%),
        linear-gradient(135deg, #f6f2e9, #efe8d7);
    }
    main {
      max-width: 1120px;
      margin: 0 auto;
      padding: 32px 20px 60px;
    }
    h1, h2, h3 { margin: 0 0 12px; line-height: 1.1; }
    h1 { font-size: 2.5rem; letter-spacing: -0.03em; }
    h2 { font-size: 1.5rem; margin-top: 28px; }
    p, li { color: var(--muted); line-height: 1.5; }
    .hero, .panel {
      background: rgba(255, 250, 240, 0.95);
      border: 1px solid var(--border);
      border-radius: 18px;
      box-shadow: 0 20px 50px rgba(64, 49, 23, 0.08);
    }
    .hero {
      padding: 26px 24px;
      margin-bottom: 24px;
    }
    .panel {
      padding: 22px 20px;
      margin-top: 18px;
    }
    form {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
      margin-top: 18px;
    }
    label {
      display: flex;
      flex-direction: column;
      gap: 6px;
      font-size: 0.95rem;
      color: var(--text);
    }
    input {
      width: 100%;
      padding: 10px 12px;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: #fff;
      color: var(--text);
      font: inherit;
    }
    button, .button-link {
      border: 0;
      border-radius: 999px;
      padding: 11px 16px;
      background: var(--accent);
      color: white;
      font: inherit;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }
    button.secondary, .button-link.secondary {
      background: var(--accent-soft);
      color: var(--accent);
    }
    .full { grid-column: 1 / -1; }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 18px;
    }
    .var-card {
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px;
      background: white;
    }
    .var-name {
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.95rem;
      color: var(--code);
      margin-bottom: 8px;
    }
    .status {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 0.8rem;
      margin-bottom: 10px;
    }
    .status.manual {
      background: var(--warn-soft);
      color: var(--warn);
    }
    pre {
      margin: 0;
      padding: 14px;
      border-radius: 14px;
      background: #19231d;
      color: #e9f2ec;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 0.9rem;
    }
    code.inline {
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      background: #f0ede3;
      padding: 2px 6px;
      border-radius: 6px;
      color: var(--code);
    }
    .hint {
      margin-top: 10px;
      font-size: 0.92rem;
      color: var(--muted);
    }
    .checks {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      margin-top: 14px;
    }
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 14px;
    }
    .actions form {
      display: block;
      margin: 0;
    }
  </style>
</head>
<body>
<main>
  <section class="hero">
    <h1>Deploy Setup Helper</h1>
    <p>This local page runs on your machine, not on the server. It helps you gather the GitHub secrets and values needed for CI-based SSH deployment to <code class="inline">root@157.22.182.58</code>.</p>
    <p>Open on <code class="inline">{{.ListenAddr}}</code>. The server binds to localhost only.</p>
  </section>

  <section class="panel">
    <h2>Remote Target</h2>
    <form method="GET" action="/">
      <label>Deploy host
        <input name="host" value="{{.Input.Host}}" placeholder="example.com or 203.0.113.10">
      </label>
      <label>Deploy user
        <input name="user" value="{{.Input.User}}" placeholder="root">
      </label>
      <label>SSH port
        <input name="port" value="{{.Input.Port}}" placeholder="22">
      </label>
      <label class="full">Deploy path on remote host
        <input name="path" value="{{.Input.Path}}" placeholder="/opt/photoshnaya">
      </label>
      <label>Docker Hub username
        <input name="dockerhub_username" value="{{.Input.DockerHubUsername}}" placeholder="{{.SuggestedDockerHubUsername}}">
      </label>
      <label>Image repository
        <input name="image_repository" value="{{.Input.ImageRepository}}" placeholder="{{.SuggestedImageRepository}}">
      </label>
      <div class="full">
        <button type="submit">Refresh values</button>
      </div>
    </form>
  </section>

  <section class="panel">
    <h2>GitHub Secrets Checklist</h2>
    <div class="grid">
      {{range .Vars}}
      <article class="var-card">
        <div class="var-name">{{.Name}}</div>
        <div class="status {{if .Manual}}manual{{end}}">{{if .Manual}}manual{{else}}derived{{end}}</div>
        <pre>{{.Value}}</pre>
        <p class="hint">{{.Hint}}</p>
      </article>
      {{end}}
    </div>
  </section>

  <section class="panel">
    <h2>SSH Derived Output</h2>
    <div class="checks">
      <div>
        <h3>Known Hosts</h3>
        <pre>{{.KnownHosts}}</pre>
      </div>
      <div>
        <h3>Remote Check</h3>
        <pre>{{.RemoteCheck}}</pre>
      </div>
    </div>
  </section>

  <section class="panel">
    <h2>Manual Helpers</h2>
    <ul>
      <li><code class="inline">DOCKERHUB_TOKEN</code> cannot be retrieved after creation, but the button opens the right Docker Hub page.</li>
      <li><code class="inline">DEPLOY_SSH_KEY</code> can be revealed locally from a chosen key under <code class="inline">~/.ssh</code>.</li>
      <li><code class="inline">DEPLOY_PATH</code> can be probed by scanning common remote directories for <code class="inline">docker-compose.yml</code>.</li>
    </ul>
    <div class="actions">
      <a class="button-link secondary" href="https://hub.docker.com/settings/security" target="_blank" rel="noreferrer">Open Docker Hub Token Page</a>
      <form method="GET" action="/">
        <input type="hidden" name="host" value="{{.Input.Host}}">
        <input type="hidden" name="user" value="{{.Input.User}}">
        <input type="hidden" name="port" value="{{.Input.Port}}">
        <input type="hidden" name="path" value="{{.Input.Path}}">
        <input type="hidden" name="dockerhub_username" value="{{.Input.DockerHubUsername}}">
        <input type="hidden" name="image_repository" value="{{.Input.ImageRepository}}">
        <input type="hidden" name="action" value="list_keys">
        <button type="submit" class="secondary">Scan Local SSH Keys</button>
      </form>
      <form method="GET" action="/">
        <input type="hidden" name="host" value="{{.Input.Host}}">
        <input type="hidden" name="user" value="{{.Input.User}}">
        <input type="hidden" name="port" value="{{.Input.Port}}">
        <input type="hidden" name="path" value="{{.Input.Path}}">
        <input type="hidden" name="dockerhub_username" value="{{.Input.DockerHubUsername}}">
        <input type="hidden" name="image_repository" value="{{.Input.ImageRepository}}">
        <input type="hidden" name="action" value="probe_paths">
        <button type="submit" class="secondary">Probe Remote Deploy Paths</button>
      </form>
    </div>
    <div class="checks">
      <div>
        <h3>SSH Keys</h3>
        <pre>{{if .SSHKeys}}{{range .SSHKeys}}{{.Path}}
{{end}}{{else}}Use "Scan Local SSH Keys" to enumerate keys from ~/.ssh.{{end}}</pre>
        {{if .SSHKeys}}
        <div class="actions">
          {{range .SSHKeys}}
          <form method="GET" action="/">
            <input type="hidden" name="host" value="{{$.Input.Host}}">
            <input type="hidden" name="user" value="{{$.Input.User}}">
            <input type="hidden" name="port" value="{{$.Input.Port}}">
            <input type="hidden" name="path" value="{{$.Input.Path}}">
            <input type="hidden" name="dockerhub_username" value="{{$.Input.DockerHubUsername}}">
            <input type="hidden" name="image_repository" value="{{$.Input.ImageRepository}}">
            <input type="hidden" name="action" value="show_key">
            <input type="hidden" name="key_path" value="{{.Path}}">
            <button type="submit" class="secondary">Reveal {{.Path}}</button>
          </form>
          {{end}}
        </div>
        {{end}}
        {{if .SelectedKey.Path}}
        <p class="hint">Selected key: <code class="inline">{{.SelectedKey.Path}}</code></p>
        {{if .SelectedKey.Error}}
        <pre>{{.SelectedKey.Error}}</pre>
        {{else}}
        <p class="hint">Public key</p>
        <pre>{{.SelectedKey.PublicKey}}</pre>
        <p class="hint">Private key for <code class="inline">DEPLOY_SSH_KEY</code></p>
        <pre>{{.SelectedKey.PrivateKey}}</pre>
        {{end}}
        {{end}}
      </div>
      <div>
        <h3>Remote Path Probe</h3>
        <pre>{{.PathProbe}}</pre>
      </div>
    </div>
  </section>
</main>
</body>
</html>`

type pageData struct {
	ListenAddr                 string
	Input                      helperInput
	SuggestedDockerHubUsername string
	SuggestedImageRepository   string
	Vars                       []varCard
	KnownHosts                 string
	RemoteCheck                string
	SSHKeys                    []sshKeyInfo
	SelectedKey                selectedKeyData
	PathProbe                  string
}

type helperInput struct {
	Host              string
	User              string
	Port              string
	Path              string
	DockerHubUsername string
	ImageRepository   string
}

type varCard struct {
	Name   string
	Value  string
	Hint   string
	Manual bool
}

type sshKeyInfo struct {
	Path    string
	PubPath string
}

type selectedKeyData struct {
	Path       string
	PublicKey  string
	PrivateKey string
	Error      string
}

type server struct {
	rootDir string
	tmpl    *template.Template
}

func main() {
	rootDir, err := os.Getwd()
	if err != nil {
		log.Fatalf("getwd: %v", err)
	}

	srv := &server{
		rootDir: rootDir,
		tmpl:    template.Must(template.New("page").Parse(pageTemplate)),
	}

	listenAddr := getenvDefault("DEPLOY_HELPER_ADDR", "127.0.0.1:8091")
	mux := http.NewServeMux()
	mux.HandleFunc("/", srv.handleIndex(listenAddr))

	log.Printf("deploy helper listening on http://%s", listenAddr)
	if err := http.ListenAndServe(listenAddr, mux); err != nil {
		log.Fatal(err)
	}
}

func (s *server) handleIndex(listenAddr string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		input := helperInput{
			Host:              defaultString(strings.TrimSpace(r.URL.Query().Get("host")), defaultDeployHost),
			User:              defaultString(strings.TrimSpace(r.URL.Query().Get("user")), defaultDeployUser),
			Port:              defaultString(strings.TrimSpace(r.URL.Query().Get("port")), defaultDeployPort),
			Path:              strings.TrimSpace(r.URL.Query().Get("path")),
			DockerHubUsername: strings.TrimSpace(r.URL.Query().Get("dockerhub_username")),
			ImageRepository:   strings.TrimSpace(r.URL.Query().Get("image_repository")),
		}
		action := strings.TrimSpace(r.URL.Query().Get("action"))
		keyPath := strings.TrimSpace(r.URL.Query().Get("key_path"))

		suggestedRepository, suggestedUsername := s.readImageDefaults()
		if input.ImageRepository == "" {
			input.ImageRepository = suggestedRepository
		}
		if input.DockerHubUsername == "" {
			input.DockerHubUsername = suggestedUsername
		}

		sshKeys := []sshKeyInfo(nil)
		selectedKey := selectedKeyData{}
		if action == "list_keys" || action == "show_key" {
			sshKeys = s.discoverSSHKeys()
		}
		if action == "show_key" && keyPath != "" {
			selectedKey = s.readSelectedKey(sshKeys, keyPath)
		}

		pathProbe := "Use \"Probe Remote Deploy Paths\" after filling host and user."
		if action == "probe_paths" {
			pathProbe = s.probeRemotePaths(input)
		}

		data := pageData{
			ListenAddr:                 listenAddr,
			Input:                      input,
			SuggestedDockerHubUsername: suggestedUsername,
			SuggestedImageRepository:   suggestedRepository,
			Vars:                       s.buildVarCards(input),
			KnownHosts:                 s.fetchKnownHosts(input.Host, input.Port),
			RemoteCheck:                s.runRemoteCheck(input),
			SSHKeys:                    sshKeys,
			SelectedKey:                selectedKey,
			PathProbe:                  pathProbe,
		}

		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		if err := s.tmpl.Execute(w, data); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
		}
	}
}

func (s *server) buildVarCards(input helperInput) []varCard {
	imageRepository := defaultString(input.ImageRepository, "your-dockerhub-user/photoshnaya_bot")

	return []varCard{
		{
			Name:  "DOCKERHUB_USERNAME",
			Value: defaultString(input.DockerHubUsername, "fill manually"),
			Hint:  "Used by the workflow to log in and build the image repository name.",
		},
		{
			Name:   "DOCKERHUB_TOKEN",
			Value:  "Open the Docker Hub token page with the helper button and create a new personal access token.",
			Hint:   "Cannot be auto-derived safely.",
			Manual: true,
		},
		{
			Name:  "DEPLOY_HOST",
			Value: defaultString(input.Host, "fill manually"),
			Hint:  "SSH host used by the deploy job.",
		},
		{
			Name:  "DEPLOY_USER",
			Value: defaultString(input.User, "fill manually"),
			Hint:  "SSH login user on the target machine.",
		},
		{
			Name:  "DEPLOY_PORT",
			Value: defaultString(input.Port, "22"),
			Hint:  "Optional, defaults to 22.",
		},
		{
			Name:  "DEPLOY_PATH",
			Value: defaultString(input.Path, "fill manually"),
			Hint:  "Checked-out directory on the remote host where docker-compose.yml lives. The helper can probe common candidates.",
		},
		{
			Name:  "DEPLOY_KNOWN_HOSTS",
			Value: s.fetchKnownHosts(input.Host, input.Port),
			Hint:  "Generated by ssh-keyscan when host is filled in.",
		},
		{
			Name:   "DEPLOY_SSH_KEY",
			Value:  "Use \"Scan Local SSH Keys\" and then reveal the exact private key you want to store as the GitHub secret.",
			Hint:   "Keep as a GitHub Actions secret. Do not commit it.",
			Manual: true,
		},
		{
			Name:  "IMAGE_REPOSITORY",
			Value: imageRepository,
			Hint:  "Not a secret, but useful to confirm what image name CI will deploy.",
		},
	}
}

func (s *server) discoverSSHKeys() []sshKeyInfo {
	homeDir, err := os.UserHomeDir()
	if err != nil {
		return nil
	}

	sshDir := filepath.Join(homeDir, ".ssh")
	entries, err := os.ReadDir(sshDir)
	if err != nil {
		return nil
	}

	keys := make([]sshKeyInfo, 0)
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}

		name := entry.Name()
		if strings.HasSuffix(name, ".pub") {
			continue
		}
		switch name {
		case "config", "known_hosts", "known_hosts.old", "authorized_keys":
			continue
		}

		keyPath := filepath.Join(sshDir, name)
		pubPath := keyPath + ".pub"
		if _, err := os.Stat(pubPath); err == nil {
			keys = append(keys, sshKeyInfo{
				Path:    keyPath,
				PubPath: pubPath,
			})
		}
	}

	return keys
}

func (s *server) readSelectedKey(keys []sshKeyInfo, keyPath string) selectedKeyData {
	for _, key := range keys {
		if key.Path != keyPath {
			continue
		}

		privateKey, privateErr := os.ReadFile(key.Path)
		if privateErr != nil {
			return selectedKeyData{Path: key.Path, Error: privateErr.Error()}
		}

		publicKey, publicErr := os.ReadFile(key.PubPath)
		if publicErr != nil {
			return selectedKeyData{
				Path:       key.Path,
				PrivateKey: strings.TrimSpace(string(privateKey)),
				Error:      publicErr.Error(),
			}
		}

		return selectedKeyData{
			Path:       key.Path,
			PublicKey:  strings.TrimSpace(string(publicKey)),
			PrivateKey: strings.TrimSpace(string(privateKey)),
		}
	}

	return selectedKeyData{
		Path:  keyPath,
		Error: "selected key was not found in ~/.ssh",
	}
}

func (s *server) readImageDefaults() (string, string) {
	composePath := filepath.Join(s.rootDir, "docker-compose.yml")
	content, err := os.ReadFile(composePath)
	if err != nil {
		return "aapq/photoshnaya_bot", "aapq"
	}

	re := regexp.MustCompile(`image:\s*\$\{IMAGE_REPOSITORY:-([^}]+)\}:\$\{IMAGE_TAG:-[^}]+\}`)
	matches := re.FindStringSubmatch(string(content))
	if len(matches) < 2 {
		return "aapq/photoshnaya_bot", "aapq"
	}

	imageRepository := strings.TrimSpace(matches[1])
	parts := strings.SplitN(imageRepository, "/", 2)
	if len(parts) == 2 {
		return imageRepository, parts[0]
	}
	return imageRepository, ""
}

func (s *server) fetchKnownHosts(host string, port string) string {
	if host == "" {
		return "Fill in the deploy host to generate this value."
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, "ssh-keyscan", "-p", defaultString(port, "22"), host)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return formatCommandError("ssh-keyscan", output, err)
	}
	trimmed := strings.TrimSpace(string(output))
	if trimmed == "" {
		return "ssh-keyscan returned no output."
	}
	return trimmed
}

func (s *server) runRemoteCheck(input helperInput) string {
	if input.Host == "" || input.User == "" || input.Path == "" {
		return "Fill in host, user, and deploy path to run the SSH validation."
	}

	script := `set -e
echo "whoami: $(whoami)"
echo "pwd: $(pwd)"
if docker compose version >/dev/null 2>&1; then
  echo "compose: docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  echo "compose: docker-compose"
else
  echo "compose: missing"
fi
DEPLOY_PATH="` + strings.ReplaceAll(input.Path, `"`, `\"`) + `"
if [ -d "$DEPLOY_PATH" ]; then
  cd "$DEPLOY_PATH"
  echo "deploy_path_exists: yes"
  echo "deploy_path_pwd: $(pwd)"
  if [ -f docker-compose.yml ]; then
    echo "compose_file: yes"
  else
    echo "compose_file: missing"
  fi
else
  echo "deploy_path_exists: no"
fi`

	ctx, cancel := context.WithTimeout(context.Background(), 8*time.Second)
	defer cancel()

	args := []string{
		"-o", "BatchMode=yes",
		"-p", defaultString(input.Port, "22"),
		fmt.Sprintf("%s@%s", input.User, input.Host),
		"sh", "-s",
	}
	cmd := exec.CommandContext(ctx, "ssh", args...)
	cmd.Stdin = strings.NewReader(script)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return formatCommandError("ssh remote check", output, err)
	}
	trimmed := strings.TrimSpace(string(output))
	if trimmed == "" {
		return "Remote check succeeded but returned no output."
	}
	return trimmed
}

func (s *server) probeRemotePaths(input helperInput) string {
	if input.Host == "" || input.User == "" {
		return "Fill in host and user first."
	}

	script := `set -e
echo "home: $HOME"
for base in "$HOME" /opt /srv /root; do
  if [ -d "$base" ]; then
    find "$base" -maxdepth 3 -name docker-compose.yml 2>/dev/null | while read -r file; do
      echo "candidate: $(dirname "$file")"
    done
  fi
done | awk '!seen[$0]++'`

	ctx, cancel := context.WithTimeout(context.Background(), 12*time.Second)
	defer cancel()

	args := []string{
		"-o", "BatchMode=yes",
		"-p", defaultString(input.Port, "22"),
		fmt.Sprintf("%s@%s", input.User, input.Host),
		"sh", "-s",
	}
	cmd := exec.CommandContext(ctx, "ssh", args...)
	cmd.Stdin = strings.NewReader(script)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return formatCommandError("ssh path probe", output, err)
	}

	trimmed := strings.TrimSpace(string(output))
	if trimmed == "" {
		return "No candidate deploy paths found."
	}
	return trimmed
}

func formatCommandError(name string, output []byte, err error) string {
	payload := map[string]string{
		"command": name,
		"error":   err.Error(),
		"output":  strings.TrimSpace(string(output)),
	}
	var buf bytes.Buffer
	encoder := json.NewEncoder(&buf)
	encoder.SetIndent("", "  ")
	if encodeErr := encoder.Encode(payload); encodeErr != nil {
		return fmt.Sprintf("%s failed: %v", name, err)
	}
	return strings.TrimSpace(buf.String())
}

func getenvDefault(name string, fallback string) string {
	if value := strings.TrimSpace(os.Getenv(name)); value != "" {
		return value
	}
	return fallback
}

func defaultString(value string, fallback string) string {
	if strings.TrimSpace(value) == "" {
		return fallback
	}
	return value
}
