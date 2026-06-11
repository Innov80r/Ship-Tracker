import axios from 'axios'

export const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function getApi(path, config = {}) {
  const { data } = await axios.get(`${API}${path}`, config)
  return data
}

export async function postApi(path, body = {}, config = {}) {
  const { data } = await axios.post(`${API}${path}`, body, config)
  return data
}

export async function putApi(path, body = {}, config = {}) {
  const { data } = await axios.put(`${API}${path}`, body, config)
  return data
}
