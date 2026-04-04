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

  // Handle empty responses (e.g., DELETE requests returning 200/204)
  const contentLength = response.headers.get('content-length');
  if (contentLength === '0' || contentLength === null) {
    return null;
  }

  return response.json();
}

export async function getBoards() {
  return fetchWithAuth(`${API_URL}/api/boards`);
}

export async function getBoard(boardId) {
  return fetchWithAuth(`${API_URL}/api/boards/${boardId}`);
}

export async function createBoard(data) {
  return fetchWithAuth(`${API_URL}/api/boards`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateBoard(boardId, data) {
  return fetchWithAuth(`${API_URL}/api/boards/${boardId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteBoard(boardId) {
  return fetchWithAuth(`${API_URL}/api/boards/${boardId}`, {
    method: 'DELETE',
  });
}

export async function deleteColumn(boardId, columnId) {
  return fetchWithAuth(`${API_URL}/api/boards/${boardId}/columns/${columnId}`, {
    method: 'DELETE',
  });
}

export async function getBoardStats(boardId) {
  return fetchWithAuth(`${API_URL}/api/boards/${boardId}/stats`);
}
