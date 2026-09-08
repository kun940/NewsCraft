/**
 * 用户模块 API
 * 对应旧接口 /api/user/*（路径、参数、响应与 V1 完全一致）
 */
import request from './request'

// 登录
export function login({ username, password }) {
  return request.post('/api/user/login', { username, password })
}

// 注册（注册成功即登录，返回 token + userInfo）
export function register({ username, password }) {
  return request.post('/api/user/register', { username, password })
}

// 获取当前用户信息（响应含可选字段 userInterestTags，旧后端无此字段时忽略）
export function getUserInfo() {
  return request.get('/api/user/info')
}

// 更新用户信息（nickname/avatar/gender/bio/phone 任选）
export function updateUserInfo(payload) {
  return request.put('/api/user/update', payload)
}

// 修改密码
export function updatePassword({ oldPassword, newPassword }) {
  return request.put('/api/user/password', { oldPassword, newPassword })
}
