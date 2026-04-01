import { useUserStore } from '../../store/userStore';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

async function fetchWithAuth(url, options = {}) {
  const { token } = useUserStore.getState();
  
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Request failed' }));
    throw new Error(error.message || 'Request failed');
  }

  return response.json();
}

export async function getTasks(boardId) {
  return fetchWithAuth(`${API_URL}/api/tasks?boardId=${boardId}`);
}

export async function getTask(taskId) {
  return fetchWithAuth(`${API_URL}/api/tasks/${taskId}`);
}

export async function createTask(data) {
  return fetchWithAuth(`${API_URL}/api/tasks`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateTask(taskId, data) {
  return fetchWithAuth(`${API_URL}/api/tasks/${taskId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function moveTask(taskId, columnId, position) {
  return fetchWithAuth(`${API_URL}/api/tasks/${taskId}/move`, {
    method: 'POST',
    body: JSON.stringify({
      target_column_id: columnId,
      new_position: position
    }),
  });
}

export async function deleteTask(taskId) {
  return fetchWithAuth(`${API_URL}/api/tasks/${taskId}`, {
    method: 'DELETE',
  });
}

export async function getComments(taskId) {
  return fetchWithAuth(`${API_URL}/api/tasks/${taskId}/comments`);
}

export async function addComment(taskId, text) {
  return fetchWithAuth(`${API_URL}/api/tasks/${taskId}/comments`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ content: text }),
  });
}

export async function deleteComment(taskId, commentId) {
  return fetchWithAuth(`${API_URL}/api/tasks/${taskId}/comments/${commentId}`, {
    method: 'DELETE',
  });
}
