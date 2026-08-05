/**
 * ATAR Ink — React + Ink terminal UI for ATAR.
 * React + Ink declarative rendering with streaming, tool cards, approval dialogs.
 */
import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Box, Text, useInput, useApp, Static } from 'ink';
import Gradient from 'ink-gradient';
import Spinner from 'ink-spinner';
import TextInput from 'ink-text-input';

// ── Types ──

interface ToolCall {
  id: string;
  name: string;
  args: Record<string, any>;
  status: 'running' | 'done' | 'error' | 'pending_approval';
  result?: string;
}

interface Message {
  role: 'user' | 'assistant' | 'tool';
  content: string;
  tool?: ToolCall;
}

type StreamingState = 'idle' | 'responding' | 'waiting_approval';

// ── Icons & Colors for Tools ──

const TOOL_CONFIG: Record<string, { icon: string; color: string }> = {
  terminal: { icon: '💻', color: '#4FC3F7' },
  read_file: { icon: '📖', color: '#81C784' },
  write_file: { icon: '✍️', color: '#FFB74D' },
  patch: { icon: '🔧', color: '#BA68C8' },
  web_search: { icon: '🔍', color: '#4DD0E1' },
  web_fetch: { icon: '🔎', color: '#4DD0E1' },
  execute_code: { icon: '⚡', color: '#FF8A65' },
  browser: { icon: '🌐', color: '#4DD0E1' },
  search_files: { icon: '🔎', color: '#4DD0E1' },
  git: { icon: '📦', color: '#F06292' },
  memory_add: { icon: '🧠', color: '#BA68C8' },
  github: { icon: '🐙', color: '#A1887F' },
  delegate_task: { icon: '🤖', color: '#4FC3F7' },
};

function getToolConfig(name: string) {
  return TOOL_CONFIG[name] || { icon: '🔧', color: '#B0BEC5' };
}

// ── Spinner (Gemini-style rainbow) ──

const GeminiSpinner: React.FC<{ active: boolean }> = ({ active }) => {
  if (!active) return null;
  return (
    <Gradient name="rainbow">
      <Spinner type="dots" />
      {' thinking...'}
    </Gradient>
  );
};

// ── Tool Card ──

const ToolCard: React.FC<{ tool: ToolCall }> = ({ tool }) => {
  const cfg = getToolConfig(tool.name);
  const statusIcon = tool.status === 'running' ? '⟳' : tool.status === 'done' ? '✓' : '✗';

  return (
    <Box flexDirection="column" marginLeft={2} marginBottom={0}>
      <Box>
        <Text color={cfg.color}>
          {cfg.icon} {tool.name}
        </Text>
        <Text dimColor> {JSON.stringify(tool.args).slice(0, 60)}</Text>
        <Text color={tool.status === 'running' ? '#FFD54F' : tool.status === 'done' ? '#81C784' : '#EF5350'}>
          {' '}{statusIcon}
        </Text>
      </Box>
      {tool.result && (
        <Text dimColor>    {tool.result.slice(0, 80).replace(/\n/g, ' ')}</Text>
      )}
    </Box>
  );
};

// ── Approval Dialog ──

const ApprovalDialog: React.FC<{
  tool: ToolCall;
  onSubmit: (approved: boolean, always: boolean) => void;
}> = ({ tool, onSubmit }) => {
  const [selected, setSelected] = useState<'y' | 'n' | 'a'>('y');

  useInput((input, key) => {
    if (key.upArrow || key.leftArrow) {
      setSelected(prev => prev === 'a' ? 'n' : prev === 'n' ? 'y' : 'a');
    } else if (key.downArrow || key.rightArrow) {
      setSelected(prev => prev === 'y' ? 'n' : prev === 'n' ? 'a' : 'y');
    } else if (key.return) {
      onSubmit(selected !== 'n', selected === 'a');
    } else if (key.escape) {
      onSubmit(false, false);
    } else if (input === 'y') {
      onSubmit(true, false);
    } else if (input === 'n') {
      onSubmit(false, false);
    } else if (input === 'a') {
      onSubmit(true, true);
    }
  });

  const cfg = getToolConfig(tool.name);

  return (
    <Box flexDirection="column" borderStyle="round" borderColor="#FFB74D" paddingX={1}>
      <Text bold color="#FFB74D">
        Approve tool execution?
      </Text>
      <Text>
        <Text color={cfg.color}>{cfg.icon} {tool.name}</Text>
        <Text dimColor> {JSON.stringify(tool.args).slice(0, 80)}</Text>
      </Text>
      <Box marginTop={1}>
        <Text color={selected === 'y' ? '#81C784' : '#616161'} bold={selected === 'y'}>
          [Y]es once
        </Text>
        <Text>  </Text>
        <Text color={selected === 'n' ? '#EF5350' : '#616161'} bold={selected === 'n'}>
          [N]o
        </Text>
        <Text>  </Text>
        <Text color={selected === 'a' ? '#64B5F6' : '#616161'} bold={selected === 'a'}>
          [A]lways
        </Text>
      </Box>
      <Text dimColor>↑↓ to select · Enter to confirm · Esc to cancel</Text>
    </Box>
  );
};

// ── Status Bar ──

const StatusBar: React.FC<{
  model: string;
  tokens: number;
  turns: number;
  tools: number;
  cost: number;
  streamingState: StreamingState;
}> = ({ model, tokens, turns, tools, cost, streamingState }) => {
  const stateIcon = streamingState === 'responding' ? '◉' : '●';
  const stateColor = streamingState === 'responding' ? '#FFD54F' : '#81C784';

  return (
    <Box justifyContent="space-between" paddingX={1}>
      <Text>
        <Text color={stateColor}>{stateIcon}</Text>
        <Text dimColor> {model}</Text>
      </Text>
      <Text dimColor>
        {tokens} tokens · {turns} turns · {tools} tools · ${cost.toFixed(3)} · {streamingState}
      </Text>
    </Box>
  );
};

// ── Chat Message ──

const ChatMessage: React.FC<{ msg: Message }> = ({ msg }) => {
  if (msg.role === 'user') {
    return (
      <Box marginBottom={0}>
        <Text bold color="#4FC3F7">▸ </Text>
        <Text>{msg.content}</Text>
      </Box>
    );
  }

  if (msg.role === 'tool' && msg.tool) {
    return <ToolCard tool={msg.tool} />;
  }

  return (
    <Box marginLeft={2} marginBottom={1}>
      <Text>{msg.content}</Text>
    </Box>
  );
};

// ── Main App ──

const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [streamingState, setStreamingState] = useState<StreamingState>('idle');
  const [pendingApproval, setPendingApproval] = useState<ToolCall | null>(null);
  const [streamingText, setStreamingText] = useState('');
  const [stats, setStats] = useState({ tokens: 0, turns: 0, tools: 0, cost: 0, model: 'deepseek-chat' });

  const { exit } = useApp();
  const responseRef = useRef('');

  // Send message to backend
  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim()) return;

    setStreamingState('responding');
    const userMsg: Message = { role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setInput('');

    try {
      // Simulate response — in production, call Python backend via HTTP
      await new Promise(r => setTimeout(r, 800));

      const assistMsg: Message = {
        role: 'assistant',
        content: `I received: "${text}". ATAR is ready to help! Try: ask me to search the web, read a file, or run a command.`,
      };
      setMessages(prev => [...prev, assistMsg]);
      setStats(prev => ({ ...prev, turns: prev.turns + 1 }));
    } finally {
      setStreamingState('idle');
    }
  }, []);

  // Keyboard bindings
  useInput((input, key) => {
    if (key.ctrl && input === 'q') {
      exit();
    }
  });

  // Submit handler
  const handleSubmit = useCallback(() => {
    if (input.trim()) {
      sendMessage(input);
    }
  }, [input, sendMessage]);

  return (
    <Box flexDirection="column" height="100%">
      {/* Header */}
      <Box paddingX={1} paddingY={0}>
        <Gradient name="rainbow">
          ┌ ATAR ─ Clarity in Complexity ─ {stats.turns} turns ─ {stats.tools} tools ┐
        </Gradient>
      </Box>

      {/* Messages area */}
      <Box flexDirection="column" flexGrow={1} paddingX={1}>
        {messages.length === 0 ? (
          <Box flexDirection="column">
            <Text dimColor>Type your message and press Enter to send.</Text>
            <Text dimColor>Ctrl+Q to quit.</Text>
          </Box>
        ) : (
          <Static items={messages}>
            {(msg: Message, idx: number) => <ChatMessage key={idx} msg={msg} />}
          </Static>
        )}
      </Box>

      {/* Spinner / Approval / Input */}
      <Box flexDirection="column" paddingX={1}>
        {pendingApproval ? (
          <ApprovalDialog
            tool={pendingApproval}
            onSubmit={(approved) => {
              setPendingApproval(null);
              setStreamingState('responding');
            }}
          />
        ) : streamingState === 'responding' ? (
          <GeminiSpinner active />
        ) : (
          <Box>
            <Text bold color="#4FC3F7">▸ </Text>
            <TextInput
              value={input}
              onChange={setInput}
              onSubmit={handleSubmit}
              placeholder="Ask ATAR..."
            />
          </Box>
        )}
      </Box>

      {/* Status bar */}
      <StatusBar {...stats} streamingState={streamingState} />
    </Box>
  );
};

export default App;
