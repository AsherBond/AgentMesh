<template>
  <div class="app">
    <!-- Task List Toggle Button -->
    <button 
      v-if="isTaskListCollapsed"
      class="floating-toggle-btn" 
      @click="toggleTaskList"
      title="Expand Task List"
    >
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M3 12h18m-9-9l9 9-9 9"/>
      </svg>
    </button>

    <!-- Task List Sidebar -->
    <div class="task-sidebar" :class="{ collapsed: isTaskListCollapsed }">
      <div class="sidebar-header">
        <button 
          class="toggle-btn" 
          @click="toggleTaskList"
          title="Collapse Task List"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M15 18l-6-6 6-6"/>
          </svg>
        </button>
        <h3 class="sidebar-title">Task List</h3>
      </div>
      
      <div class="task-list">
        <div v-if="tasks.length === 0" class="empty-state">
          <p>No tasks yet</p>
          <p class="empty-hint">Tasks will appear here after you start a conversation</p>
        </div>
        <div v-else>
          <div 
            v-for="task in tasks" 
            :key="task.id"
            class="task-item"
            :class="{ active: task.status === 'running', completed: task.status === 'completed' }"
          >
            <div class="task-status">
              <div class="status-indicator" :class="task.status"></div>
            </div>
            <div class="task-content">
              <h4 class="task-title">{{ task.title }}</h4>
              <p class="task-description">{{ task.description }}</p>
              <div class="task-meta">
                <span class="task-time">{{ formatTime(task.timestamp) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content Area -->
    <div class="main-content" :class="{ expanded: isTaskListCollapsed }">
      <!-- Main Content Area -->
      <div class="content-area">
        <!-- Split View for Agent Process and Tool Results -->
        <div v-if="messages.length > 0" class="split-view" ref="messagesContainer">
          <!-- Left Panel: Agent Process and Input -->
          <div class="left-panel">
            <!-- Agent Process Section -->
            <div class="agent-process-panel">
              <div class="panel-header">
                <h3 class="panel-title">Agent Process</h3>
                <div class="panel-status">
                  <span class="status-dot" :class="{ active: isAgentRunning }"></span>
                  <span class="status-text">{{ isAgentRunning ? 'Running' : 'Completed' }}</span>
                </div>
              </div>
                          <div class="process-content">
              <div 
                v-for="agent in agentMessages" 
                :key="agent.id"
                class="agent-message"
              >
                <div class="agent-avatar">
                  <img :src="agent.avatar" :alt="agent.name" class="avatar-img">
                </div>
                <div class="agent-content">
                  <div class="agent-bubble">
                    <div class="agent-header">
                      <span class="agent-name">{{ agent.name }}</span>
                      <span class="agent-timestamp">{{ formatLogTime(agent.timestamp) }}</span>
                    </div>
                    
                    <!-- Task received -->
                    <div v-if="agent.task" class="content-section">
                      <div class="section-label">
                        <span class="section-icon">📋</span>
                        <span class="section-title">Task Received</span>
                      </div>
                      <div class="section-text">{{ agent.task }}</div>
                    </div>
                    
                    <!-- Thinking process -->
                    <div v-if="agent.thinking" class="content-section">
                      <div class="section-label">
                        <span class="section-icon">🧠</span>
                        <span class="section-title">Thinking</span>
                      </div>
                      <div class="section-text">{{ agent.thinking }}</div>
                    </div>
                    
                    <!-- Tool execution -->
                    <div v-if="agent.tools && agent.tools.length > 0" class="content-section">
                      <div 
                        v-for="tool in agent.tools" 
                        :key="tool.id"
                        class="tool-item"
                      >
                        <div class="section-label">
                          <span class="section-icon">🛠️</span>
                          <span class="section-title">{{ tool.name }}</span>
                        </div>
                        <div class="section-text tool-params">{{ tool.params }}</div>
                      </div>
                    </div>
                    
                    <!-- Response/Output -->
                    <div v-if="agent.response" class="content-section">
                      <div class="section-label">
                        <span class="section-icon">💬</span>
                        <span class="section-title">Response</span>
                      </div>
                      <div class="section-text" v-html="formatResponse(agent.response)"></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            </div>

            <!-- Input Area for conversation mode -->
            <div class="conversation-input-section">
              <div class="input-container">
                <div class="input-wrapper">
                  <textarea
                    v-model="inputMessage"
                    @keydown="handleKeyDown"
                    placeholder="Enter your task"
                    class="chat-input"
                    rows="1"
                    ref="chatInput"
                  ></textarea>
                  <div class="input-actions">
                    <button class="action-btn" title="Upload File">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66L9.64 16.2a2 2 0 0 1-2.83-2.83l8.49-8.49"/>
                      </svg>
                    </button>
                    <button class="action-btn" title="Voice Input">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
                        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                        <path d="M12 19v3"/>
                      </svg>
                    </button>
                    <button class="action-btn" title="More Options">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="1"/>
                        <circle cx="19" cy="12" r="1"/>
                        <circle cx="5" cy="12" r="1"/>
                      </svg>
                    </button>
                    <button 
                      @click="sendMessage"
                      :disabled="!inputMessage.trim() || isLoading"
                      class="send-btn"
                    >
                      <svg v-if="!isLoading" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 2L11 13"/>
                        <path d="M22 2L15 22L11 13L2 9L22 2Z"/>
                      </svg>
                      <div v-else class="loading-spinner"></div>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Right Panel: Tool Results (Full Height) -->
          <div class="tool-results-panel">
            <div class="panel-header">
              <h3 class="panel-title">Tool Execution Results</h3>
              <div class="tool-tabs">
                <button 
                  v-for="tool in activeTools" 
                  :key="tool.id"
                  class="tool-tab"
                  :class="{ active: selectedTool === tool.id }"
                  @click="selectedTool = tool.id"
                >
                  <span class="tool-tab-icon">{{ tool.icon }}</span>
                  <span class="tool-tab-name">{{ tool.name }}</span>
                </button>
              </div>
            </div>
            <div class="tool-content">
              <div v-if="selectedToolData" class="tool-result">
                <div v-if="selectedToolData.type === 'search'" class="search-result">
                  <h4>Search Results</h4>
                  <div class="search-query">Query: {{ selectedToolData.query }}</div>
                  <div class="search-items">
                    <div v-for="item in selectedToolData.results" :key="item.id" class="search-item">
                      <h5 class="search-title">{{ item.title }}</h5>
                      <p class="search-snippet">{{ item.snippet }}</p>
                      <a :href="item.url" class="search-url" target="_blank">{{ item.url }}</a>
                    </div>
                  </div>
                </div>
                <div v-else-if="selectedToolData.type === 'terminal'" class="terminal-result">
                  <h4>Terminal Execution</h4>
                  <div class="terminal-command">$ {{ selectedToolData.command }}</div>
                  <pre class="terminal-output">{{ selectedToolData.output }}</pre>
                </div>
                <div v-else-if="selectedToolData.type === 'file'" class="file-result">
                  <h4>File Content</h4>
                  <div class="file-path">{{ selectedToolData.path }}</div>
                  <pre class="file-content">{{ selectedToolData.content }}</pre>
                </div>
              </div>
              <div v-else class="empty-tool-result">
                <p>Select a tool from the left to view execution results</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Welcome Section with centered input -->
        <div v-else class="welcome-section">
          <div class="welcome-content">
            <div class="title-section">
              <h1 class="main-title">AgentMesh</h1>
              <p class="subtitle">Let multi-agent teams help you complete various tasks</p>
            </div>
            
            <!-- Centered Input Area -->
            <div class="center-input-section">
              <div class="input-wrapper">
                <textarea
                  v-model="inputMessage"
                  @keydown="handleKeyDown"
                  placeholder="Enter your task"
                  class="chat-input"
                  rows="1"
                  ref="chatInput"
                ></textarea>
                <div class="input-actions">
                  <button class="action-btn" title="Upload File">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66L9.64 16.2a2 2 0 0 1-2.83-2.83l8.49-8.49"/>
                    </svg>
                  </button>
                  <button class="action-btn" title="Voice Input">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
                      <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                      <path d="M12 19v3"/>
                    </svg>
                  </button>
                  <button class="action-btn" title="More Options">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <circle cx="12" cy="12" r="1"/>
                      <circle cx="19" cy="12" r="1"/>
                      <circle cx="5" cy="12" r="1"/>
                    </svg>
                  </button>
                  <button 
                    @click="sendMessage"
                    :disabled="!inputMessage.trim() || isLoading"
                    class="send-btn"
                  >
                    <svg v-if="!isLoading" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M22 2L11 13"/>
                      <path d="M22 2L15 22L11 13L2 9L22 2Z"/>
                    </svg>
                    <div v-else class="loading-spinner"></div>
                  </button>
                </div>
              </div>
            </div>

            <!-- Example prompts below input -->
            <div class="example-prompts">
              <button 
                v-for="example in examplePrompts" 
                :key="example"
                class="example-btn"
                @click="setInputValue(example)"
              >
                <span class="example-icon">💡</span>
                {{ example }}
              </button>
            </div>
          </div>
        </div>


      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, computed } from 'vue'
import productAvatar from './assets/product.png'
import developerAvatar from './assets/developer.png'

// Reactive data
const isTaskListCollapsed = ref(true)
const inputMessage = ref('')
const isLoading = ref(false)
const messages = ref([])
const tasks = ref([])
const messagesContainer = ref(null)
const chatInput = ref(null)
const isAgentRunning = ref(false)
const selectedTool = ref(null)
const agentLogs = ref([])
const activeTools = ref([])
const agentMessages = ref([])

// Example prompts for users
const examplePrompts = [
  "Generate a comprehensive quarterly business performance report",
  "Create a Python web scraper for e-commerce product data",
  "Build a React dashboard with real-time analytics charts",
  "Generate a technical documentation report for API endpoints"
]

// Methods
const toggleTaskList = () => {
  isTaskListCollapsed.value = !isTaskListCollapsed.value
}

const setInputValue = (value) => {
  inputMessage.value = value
  nextTick(() => {
    chatInput.value?.focus()
  })
}

const handleKeyDown = (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

const sendMessage = async () => {
  if (!inputMessage.value.trim() || isLoading.value) return

  const userMessage = {
    id: Date.now(),
    type: 'user',
    sender: 'You',
    content: inputMessage.value.trim(),
    timestamp: new Date()
  }

  messages.value.push(userMessage)
  
  // Create a new task
  const newTask = {
    id: Date.now(),
    title: inputMessage.value.substring(0, 50) + (inputMessage.value.length > 50 ? '...' : ''),
    description: inputMessage.value,
    agent: 'Task Coordinator',
    status: 'running',
    createdAt: new Date()
  }
  
  tasks.value.unshift(newTask)
  
  const userInput = inputMessage.value
  inputMessage.value = ''
  isLoading.value = true
  isAgentRunning.value = true

  // Auto-expand task list when starting conversation
  if (messages.value.length === 1) {
    isTaskListCollapsed.value = false
  }

  // Initialize mock data for demonstration
  initializeMockData()

  // Simulate system response (replace with actual API call)
  setTimeout(() => {
    const systemMessage = {
      id: Date.now() + 1,
      type: 'system',
      sender: 'AgentMesh',
      content: `I have received your request: "${userInput}". The agent team is analyzing your task and will start processing soon. You can monitor the progress in the task list on the left.`,
      timestamp: new Date()
    }
    
    messages.value.push(systemMessage)
    isLoading.value = false
    
    // Update task status after a delay
    setTimeout(() => {
      newTask.status = 'completed'
      isAgentRunning.value = false
    }, 5000)
    
    scrollToBottom()
  }, 1000)

  scrollToBottom()
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const formatTime = (date) => {
  return new Intl.DateTimeFormat('en-US', {
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}

const formatLogTime = (date) => {
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  }).format(date)
}

const formatResponse = (response) => {
  if (!response) return ''
  // Convert markdown-like content to HTML for better display
  return response
    .replace(/\n/g, '<br>')
    .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre class="code-block"><code>$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
}

// Computed property for task list visibility
const shouldShowTaskList = computed(() => {
  // In conversation mode, show task list by default
  if (messages.value.length > 0) {
    return !isTaskListCollapsed.value
  }
  // In welcome mode, hide task list by default
  return !isTaskListCollapsed.value
})

// Computed property for selected tool data
const selectedToolData = computed(() => {
  if (!selectedTool.value) return null
  const tool = activeTools.value.find(t => t.id === selectedTool.value)
  return tool?.data || null
})

// Mock data for demonstration
const initializeMockData = () => {
  // Legacy log data
  agentLogs.value = [
    {
      id: 1,
      type: 'info',
      timestamp: new Date(),
      message: 'Team Super Assistant Team received the task and started processing'
    },
    {
      id: 2,
      type: 'agent',
      timestamp: new Date(),
      agentName: 'AI Search Assistant',
      task: 'Search for AgentMesh framework information',
      thinking: 'Need to search the web for AgentMesh\'s latest framework information to understand its multi-agent capabilities and features.',
      tool: {
        name: 'google_search',
        params: '{"query": "AgentMesh multi-agent framework 2025"}'
      }
    },
    {
      id: 3,
      type: 'info',
      timestamp: new Date(),
      message: '🧠 Need to search the web for AgentMesh\'s latest framework information to understand its multi-agent capabilities and features.'
    },
    {
      id: 4,
      type: 'info',
      timestamp: new Date(),
      message: '🛠️ google_search: {"query": "AgentMesh multi-agent framework 2025"}'
    },
    {
      id: 5,
      type: 'agent',
      timestamp: new Date(),
      agentName: 'AI Search Assistant',
      thinking: 'Based on the search results, AgentMesh\'s latest framework information shows version 2.0 release on January 15, 2025, which includes enhanced agent communication protocols, distributed task execution, and intelligent workflow coordination capabilities.',
      response: 'AgentMesh\'s latest release is version 2.0 launched on January 15, 2025. The main features include enhanced agent communication protocols, distributed task execution capabilities, and intelligent workflow coordination. This framework provides comprehensive tools for building multi-agent systems with real-time monitoring and flexible team configuration options.'
    },
    {
      id: 6,
      type: 'info',
      timestamp: new Date(),
      message: 'Team Super Assistant Team completed the task'
    }
  ]

  // New agent messages format
  agentMessages.value = [
    {
      id: 1,
      name: 'Product-Manager',
      avatar: productAvatar,
      timestamp: new Date(Date.now() - 300000),
      task: 'Please write a Product Requirements Document (PRD) for a Snake game, including core gameplay, basic features, and user experience requirements.',
      thinking: 'The current task is to write a PRD for a Snake game, covering core gameplay, basic features, and user experience requirements. No tools need to be called, I can directly output a detailed product requirements document.',
      tools: [
        {
          id: 1,
          name: 'File Save',
          params: 'workspace/software_team/snake_game_development/snake_game_prd.md'
        }
      ],
      response: `# Snake Game Product Requirements Document (PRD)

## 1. Product Overview
Snake is a classic casual puzzle game where players control the snake's movement direction, eat food on the map to make the snake longer, while avoiding hitting walls and the snake's body. The game is simple and easy to learn, suitable for users of all ages.

## 2. Core Gameplay
1. **Control Method** - Players control the snake's movement direction through arrow keys (up, down, left, right) or touch screen swipes.
2. **Objective** - Eat randomly appearing food on the map. Each food eaten increases the snake's length by one segment and increases the score.
3. **Scoring System** - Each food eaten earns 1 point. The current score and historical high score are displayed when the game ends.`
    },
    {
      id: 2,
      name: 'Developer',
      avatar: developerAvatar,
      timestamp: new Date(Date.now() - 120000),
      task: 'Based on the Snake game PRD provided by the product manager, implement a single-page web Snake game with adaptive layout, keyboard and touch screen support, start/pause/restart, leaderboard, sound effects, difficulty selection and other features.',
      thinking: 'According to the PRD, need to implement a single-page web Snake game with adaptive layout, keyboard and touch screen support, start/pause/restart, leaderboard, sound effects, difficulty selection and other features. Next step should output a complete HTML file with clear structure, including CSS and JavaScript, meeting all core gameplay and user experience requirements.',
      response: `\`\`\`import pygame
import random
import sys
from enum import Enum

# Initialize pygame
pygame.init()

# Define color constants
class Colors:
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    YELLOW = (255, 255, 0)
    DARK_GREEN = (0, 128, 0)
    LIGHT_GREEN = (144, 238, 144)

# Define direction enum
class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

class SnakeGame:
    def __init__(self, width=800, height=600, cell_size=20):
        self.width = width
        self.
\`\`\``
    }
  ]

  activeTools.value = [
    {
      id: 'search1',
      name: 'Web Search',
      icon: '🔍',
      data: {
        type: 'search',
        query: 'AgentMesh multi-agent framework 2025',
        results: [
          {
            id: 1,
            title: 'AgentMesh 2.0 Release - Advanced Multi-Agent Orchestration Framework',
            snippet: 'AgentMesh platform released version 2.0 on January 15, 2025, featuring enhanced agent communication protocols, distributed task execution, and intelligent workflow coordination...',
            url: 'https://github.com/MinimalFuture/AgentMesh'
          },
          {
            id: 2,
            title: 'AgentMesh Documentation - Getting Started with Multi-Agent Systems',
            snippet: 'Comprehensive guide to building and deploying multi-agent systems using AgentMesh framework, including team configuration, task distribution, and real-time monitoring...',
            url: 'https://github.com/MinimalFuture/AgentMesh'
          },
          {
            id: 3,
            title: 'AgentMesh Tool Ecosystem - Extensible Agent Capabilities',
            snippet: 'The latest version includes a rich ecosystem of tools for agent interaction, including web browsing, file operations, search capabilities, and custom tool integration...',
            url: 'https://github.com/MinimalFuture/AgentMesh'
          }
        ]
      }
    }
  ]
  
  selectedTool.value = 'search1'
  
  // Add some sample tasks
  tasks.value = [
    {
      id: 1,
      title: 'AgentMesh Framework Research and Analysis',
      description: 'I will use search tools to retrieve "AgentMesh" related information, including framework capabilities, multi-agent features, etc.',
      status: 'completed',
      timestamp: new Date(Date.now() - 300000)
    },
    {
      id: 2,
      title: 'Multi-Agent System Configuration',
      description: 'I am configuring the agent team structure and defining communication protocols for optimal task execution.',
      status: 'running',
      timestamp: new Date(Date.now() - 120000)
    },
    {
      id: 3,
      title: 'AgentMesh Documentation Review',
      description: 'I will review the AgentMesh documentation to understand best practices for agent coordination.',
      status: 'pending',
      timestamp: new Date(Date.now() - 60000)
    },
    {
      id: 4,
      title: 'Agent Performance Monitoring Setup',
      description: 'I will set up real-time monitoring for agent performance and task execution metrics.',
      status: 'pending',
      timestamp: new Date()
    }
  ]
}

// Auto-resize textarea
onMounted(() => {
  const textarea = chatInput.value
  if (textarea) {
    textarea.addEventListener('input', () => {
      textarea.style.height = 'auto'
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px'
    })
  }
})
</script>

<style scoped>
.app {
  display: flex;
  height: 100vh;
  background: linear-gradient(135deg, #fafbfc 0%, #f1f5f9 50%, #e2e8f0 100%);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  overflow: hidden;
}

/* Floating Toggle Button */
.floating-toggle-btn {
  position: fixed;
  top: 20px;
  left: 20px;
  z-index: 1001;
  background: rgba(255, 255, 255, 0.9);
  color: #6b7280;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 12px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
}

.floating-toggle-btn:hover {
  background: rgba(255, 255, 255, 1);
  color: #374151;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
}

/* Task Sidebar */
.task-sidebar {
  width: 280px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-right: 1px solid rgba(255, 255, 255, 0.2);
  display: flex;
  flex-direction: column;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.task-sidebar.collapsed {
  width: 0;
  border-right: none;
  overflow: hidden;
}

.sidebar-header {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  gap: 12px;
  height: 56px;
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.95);
}

.toggle-btn {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(0, 0, 0, 0.08);
  cursor: pointer;
  padding: 10px;
  border-radius: 12px;
  color: #6b7280;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(10px);
}

.toggle-btn:hover {
  background: rgba(255, 255, 255, 1);
  color: #374151;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.sidebar-title {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
  margin: 0;
}

.task-list {
  padding: 16px;
  overflow-y: auto;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #9ca3af;
}

.empty-state p {
  margin-bottom: 8px;
  font-size: 14px;
}

.empty-hint {
  font-size: 12px;
  opacity: 0.7;
}

.task-item {
  display: flex;
  gap: 10px;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 6px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(0, 0, 0, 0.08);
  transition: all 0.2s ease;
  cursor: pointer;
  min-height: 60px;
}

.task-item:hover {
  background: rgba(255, 255, 255, 1);
  border-color: rgba(0, 0, 0, 0.12);
}

.task-item.active {
  background: rgba(255, 255, 255, 1);
  border-color: #3370ff;
  box-shadow: 0 0 0 1px rgba(51, 112, 255, 0.2);
}

.task-item.completed {
  background: rgba(255, 255, 255, 0.8);
  opacity: 0.8;
}

.task-item.running {
  border-color: #3370ff;
  background: rgba(255, 255, 255, 1);
}

.task-status {
  flex-shrink: 0;
  padding-top: 4px;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #d1d5db;
  flex-shrink: 0;
}

.status-indicator.running {
  background: #6b7280;
  animation: pulse 2s infinite;
}

.status-indicator.completed {
  background: #9ca3af;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.task-content {
  flex: 1;
  min-width: 0;
}

.task-title {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 2px;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-description {
  font-size: 12px;
  color: #6b7280;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  color: #9ca3af;
  margin-top: 4px;
}

/* Main Content */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
  position: relative;
}

.main-content.expanded {
  margin-left: 0;
}



/* Content Area */
.content-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
}

/* Welcome Section - Centered Layout */
.welcome-section {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 20px;
  min-height: calc(100vh - 140px);
}

.welcome-content {
  width: 100%;
  max-width: 800px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 40px;
}

.title-section {
  text-align: center;
}

.main-title {
  font-size: 48px;
  font-weight: 700;
  background: linear-gradient(135deg, #3370ff 0%, #1e40af 50%, #0ea5e9 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 16px;
  line-height: 1.2;
  letter-spacing: -0.02em;
  text-shadow: 0 0 30px rgba(51, 112, 255, 0.3);
}

.subtitle {
  font-size: 18px;
  color: #6b7280;
  margin: 0;
  font-weight: 400;
}

/* Centered Input Section */
.center-input-section {
  width: 100%;
  max-width: 700px;
}

.center-input-section .input-wrapper {
  display: flex;
  align-items: flex-start;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 20px;
  padding: 24px 28px;
  backdrop-filter: blur(20px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  min-height: 200px;
}

.center-input-section .input-wrapper:focus-within {
  border-color: #3370ff;
  box-shadow: 0 8px 32px rgba(51, 112, 255, 0.3);
  transform: translateY(-2px);
}

.center-input-section .chat-input {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  font-size: 18px;
  line-height: 1.5;
  font-family: inherit;
  min-height: 140px;
  max-height: 140px;
  background: transparent;
  color: #374151;
  vertical-align: top;
}

.example-prompts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  width: 100%;
  max-width: 700px;
}

.example-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: left;
  font-size: 13px;
  color: #374151;
  backdrop-filter: blur(10px);
}

.example-btn:hover {
  background: rgba(255, 255, 255, 0.95);
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
}

.example-icon {
  font-size: 16px;
}

/* Split View Layout */
.split-view {
  flex: 1;
  display: flex;
  gap: 1px;
  background: #e2e8f0;
  overflow: hidden;
  min-height: 0;
}

/* Left Panel containing Agent Process and Input */
.left-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-left: 1px solid rgba(0, 0, 0, 0.1);
  min-height: 0;
}

/* Agent Process Panel */
.agent-process-panel {
  flex: 1 0 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.panel-header {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.95);
  height: 56px;
  flex-shrink: 0;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  margin: 0;
}

.panel-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #d1d5db;
  transition: all 0.3s ease;
}

.status-dot.active {
  background: #3370ff;
  animation: pulse 2s infinite;
  box-shadow: 0 0 0 4px rgba(51, 112, 255, 0.3);
}

.status-text {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
}

.process-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 0;
}

.process-content::-webkit-scrollbar {
  width: 6px;
}

.process-content::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.05);
  border-radius: 3px;
}

.process-content::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
}

.process-content::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.3);
}

.log-entry {
  margin-bottom: 16px;
  padding: 12px;
  border-radius: 8px;
  background: rgba(248, 250, 252, 0.8);
  border-left: 3px solid #e2e8f0;
}

.log-entry.info {
  border-left-color: #6b7280;
}

.log-entry.agent {
  border-left-color: #3370ff;
  background: rgba(51, 112, 255, 0.02);
}

.log-timestamp {
  font-size: 11px;
  color: #9ca3af;
  margin-bottom: 6px;
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
}

.log-content {
  font-size: 13px;
  line-height: 1.5;
}

.log-info {
  color: #4b5563;
}

.log-level {
  color: #6b7280;
  font-weight: 600;
  margin-right: 8px;
}

.log-message {
  color: #374151;
}

.agent-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-weight: 600;
}

.agent-icon {
  font-size: 14px;
}

.agent-name {
  color: #3370ff;
  font-size: 14px;
}

.agent-task {
  color: #6b7280;
  font-size: 12px;
  font-weight: 400;
}

.agent-thinking,
.agent-tool,
.agent-response {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 6px;
}

.thinking-icon,
.tool-icon,
.response-icon {
  font-size: 14px;
  margin-top: 1px;
}

.thinking-text {
  color: #4b5563;
  font-style: italic;
}

.tool-name {
  color: #059669;
  font-weight: 600;
}

.tool-params {
  color: #6b7280;
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
  font-size: 12px;
}

.response-text {
  color: #374151;
}

/* Agent Message Styles */
.agent-message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.agent-avatar {
  flex-shrink: 0;
}

.avatar-img {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.8);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.agent-content {
  flex: 1;
  min-width: 0;
}

.agent-bubble {
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  backdrop-filter: blur(10px);
}

.agent-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.agent-name {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
}

.agent-timestamp {
  font-size: 12px;
  color: #9ca3af;
}

.content-section {
  margin-bottom: 16px;
}

.content-section:last-child {
  margin-bottom: 0;
}

.section-label {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  font-weight: 600;
  font-size: 12px;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.section-icon {
  font-size: 14px;
}

.section-title {
  color: #6b7280;
}

.section-text {
  font-size: 13px;
  line-height: 1.6;
  color: #374151;
  margin-left: 20px;
}

.tool-item {
  margin-bottom: 12px;
}

.tool-item:last-child {
  margin-bottom: 0;
}

.tool-params {
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
  font-size: 12px;
  color: #059669;
  background: rgba(5, 150, 105, 0.08);
  padding: 6px 10px;
  border-radius: 6px;
  margin-top: 4px;
  border: 1px solid rgba(5, 150, 105, 0.15);
}

.code-block {
  background: rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 6px;
  padding: 12px;
  margin: 8px 0;
  overflow-x: auto;
}

.code-block code {
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
  font-size: 12px;
  color: #374151;
  white-space: pre;
}

.inline-code {
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
  font-size: 12px;
  background: rgba(0, 0, 0, 0.05);
  padding: 2px 4px;
  border-radius: 3px;
  color: #059669;
}

/* Tool Results Panel */
.tool-results-panel {
  flex: 1;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.tool-tabs {
  display: flex;
  gap: 4px;
}

.tool-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: transparent;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 12px;
  color: #6b7280;
}

.tool-tab:hover {
  background: rgba(51, 112, 255, 0.1);
  color: #3370ff;
}

.tool-tab.active {
  background: #3370ff;
  color: white;
}

.tool-tab-icon {
  font-size: 14px;
}

.tool-tab-name {
  font-weight: 500;
}

.tool-content {
  flex: 1 0 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 20px;
  min-height: 0;
  height: 1px;
}

.tool-result h4 {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  margin: 0 0 12px 0;
}

.search-query {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 16px;
  padding: 8px 12px;
  background: rgba(107, 114, 128, 0.1);
  border-radius: 6px;
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
}

.search-items {
  space-y: 12px;
}

.search-item {
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  margin-bottom: 12px;
  background: rgba(249, 250, 251, 0.8);
}

.search-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 6px 0;
  line-height: 1.4;
}

.search-snippet {
  font-size: 13px;
  color: #4b5563;
  line-height: 1.5;
  margin: 0 0 8px 0;
}

.search-url {
  font-size: 12px;
  color: #3370ff;
  text-decoration: none;
  word-break: break-all;
}

.search-url:hover {
  text-decoration: underline;
}

.terminal-command {
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
  font-size: 12px;
  color: #059669;
  background: rgba(5, 150, 105, 0.1);
  padding: 8px 12px;
  border-radius: 6px;
  margin-bottom: 12px;
}

.terminal-output {
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
  font-size: 12px;
  color: #374151;
  background: rgba(0, 0, 0, 0.05);
  padding: 12px;
  border-radius: 6px;
  white-space: pre-wrap;
  overflow-x: auto;
}

.file-path {
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
  font-size: 12px;
  color: #6b7280;
  background: rgba(107, 114, 128, 0.1);
  padding: 8px 12px;
  border-radius: 6px;
  margin-bottom: 12px;
}

.file-content {
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
  font-size: 12px;
  color: #374151;
  background: rgba(249, 250, 251, 0.8);
  padding: 12px;
  border-radius: 6px;
  white-space: pre-wrap;
  overflow-x: auto;
  border: 1px solid #e5e7eb;
}

.empty-tool-result {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #9ca3af;
  font-size: 14px;
}

.message {
  margin-bottom: 24px;
}

.message.user .message-content {
  background: rgba(59, 130, 246, 0.1);
  color: #374151;
  margin-left: 80px;
  border: 1px solid rgba(59, 130, 246, 0.2);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
}

.message.system .message-content {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.3);
  margin-right: 80px;
  backdrop-filter: blur(10px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.message-content {
  padding: 20px;
  border-radius: 16px;
  transition: all 0.3s ease;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 12px;
  opacity: 0.8;
}

.message-sender {
  font-weight: 600;
}

.message-text {
  line-height: 1.6;
  white-space: pre-wrap;
}

/* Fixed Input Section for conversation mode */
.fixed-input-section {
  padding: 20px;
  background: transparent;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(10px);
}

/* Conversation Input Section in Split View */
.conversation-input-section {
  padding: 16px 20px;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  background: rgba(248, 250, 252, 0.5);
  flex-shrink: 0;
}

.input-container {
  max-width: 700px;
  margin: 0 auto;
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 20px;
  padding: 16px 20px;
  backdrop-filter: blur(20px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.input-wrapper:focus-within {
  border-color: #3370ff;
  box-shadow: 0 8px 32px rgba(51, 112, 255, 0.3);
  transform: translateY(-2px);
}

.chat-input {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  font-size: 16px;
  line-height: 1.5;
  font-family: inherit;
  min-height: 24px;
  max-height: 120px;
  background: transparent;
  color: #374151;
}

.chat-input::placeholder {
  color: #9ca3af;
  text-align: start;
  line-height: 1.5;
}

/* Special styles for conversation input to center placeholder */
.conversation-input-section .chat-input {
  min-height: 40px;
  padding-top: 8px;
  padding-bottom: 8px;
}

.conversation-input-section .input-wrapper {
  align-items: center;
  min-height: 56px;
}

.input-actions {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  margin-left: 12px;
  align-self: flex-end;
}

.action-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 8px;
  border-radius: 8px;
  color: #9ca3af;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-btn:hover {
  background: rgba(51, 112, 255, 0.1);
  color: #3370ff;
}

.send-btn {
  background: linear-gradient(135deg, #3370ff 0%, #1e40af 100%);
  color: white;
  border: none;
  border-radius: 12px;
  padding: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 40px;
  height: 40px;
  box-shadow: 0 4px 15px rgba(51, 112, 255, 0.4);
}

.send-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #1e40af 0%, #1e3a8a 100%);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(51, 112, 255, 0.6);
}

.send-btn:disabled {
  background: #d1d5db;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top: 2px solid white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 768px) {
  .task-sidebar {
    position: fixed;
    left: 0;
    top: 0;
    height: 100vh;
    z-index: 1000;
    transform: translateX(-100%);
    transition: transform 0.3s ease;
  }

  .task-sidebar:not(.collapsed) {
    transform: translateX(0);
  }

  .task-sidebar.collapsed {
    width: 0;
    transform: translateX(-100%);
  }

      .main-content {
      margin-left: 0;
    }



  .main-title {
    font-size: 36px;
  }

  .subtitle {
    font-size: 16px;
  }

  .example-prompts {
    grid-template-columns: 1fr;
  }

  .message.user .message-content {
    margin-left: 20px;
  }

  .message.system .message-content {
    margin-right: 20px;
  }

  .fixed-input-section {
    padding: 16px;
  }

  .center-input-section .input-wrapper {
    padding: 20px 24px;
    min-height: 160px;
    align-items: flex-start;
  }

  .center-input-section .chat-input {
    font-size: 16px;
    min-height: 100px;
    max-height: 100px;
  }

  /* Mobile Split View */
  .split-view {
    flex-direction: column;
  }

  .left-panel {
    flex: 1;
  }

  .tool-results-panel {
    flex: 1;
    min-height: 300px;
  }

  .process-content {
    flex: 1;
    min-height: 0;
    max-height: calc(50vh - 100px);
  }

  .tool-tabs {
    flex-wrap: wrap;
  }
}

/* Scrollbar styling */
.task-list::-webkit-scrollbar,
.chat-messages::-webkit-scrollbar {
  width: 6px;
}

.task-list::-webkit-scrollbar-track,
.chat-messages::-webkit-scrollbar-track {
  background: transparent;
}

.task-list::-webkit-scrollbar-thumb,
.chat-messages::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
}

.task-list::-webkit-scrollbar-thumb:hover,
.chat-messages::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.3);
}
</style> 