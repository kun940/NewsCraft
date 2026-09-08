import { defineStore } from 'pinia';
import * as userApi from '../api/user';

export const useUserStore = defineStore('user', {
  state: () => ({
    userInfo: null,
    token: '',
    isLogin: false,
    userBio: '这是我的个人简介'
  }),
  
  getters: {
    getUserInfo: (state) => state.userInfo,
    getToken: (state) => state.token,
    getLoginStatus: (state) => state.isLogin,
    getUserBio: (state) => state.userInfo?.bio || state.userBio
  },
  
  actions: {
    async login(userData) {
      try {
        const data = await userApi.login({
          username: userData.username,
          password: userData.password
        });
        
        this.userInfo = data.userInfo;
        this.token = data.token;
        this.isLogin = true;
        
        return {
          success: true,
          message: '登录成功'
        };
      } catch (error) {
        console.error('登录请求失败:', error);
        return {
          success: false,
          message: error?.message || '登录请求失败，请稍后再试'
        };
      }
    },
    
    async register(userData) {
      try {
        const data = await userApi.register({
          username: userData.username,
          password: userData.password
        });
        
        // 注册成功，自动登录
        this.userInfo = data.userInfo;
        this.token = data.token;
        this.isLogin = true;
        
        return {
          success: true,
          message: '注册成功'
        };
      } catch (error) {
        console.error('注册请求失败:', error);
        return {
          success: false,
          message: error?.message || '注册请求失败，请稍后再试'
        };
      }
    },
    
    logout() {
      this.userInfo = null;
      this.token = '';
      this.isLogin = false;
    },
    
    // 获取用户信息
    async getUserInfoDetail() {
      try {
        if (!this.token) {
          return {
            success: false,
            message: '未登录'
          };
        }
        
        const data = await userApi.getUserInfo();
        
        this.userInfo = data;
        
        return {
          success: true,
          message: '获取用户信息成功',
          data
        };
      } catch (error) {
        console.error('获取用户信息请求失败:', error);
        return {
          success: false,
          message: error?.message || '获取用户信息请求失败，请稍后再试'
        };
      }
    },
    
    // 更新个人简介
    async updateUserBio(bio) {
      try {
        if (!this.token) {
          return {
            success: false,
            message: '未登录'
          };
        }
        
        const data = await userApi.updateUserInfo({ bio });
        
        this.userInfo = data;
        
        return {
          success: true,
          message: '更新个人简介成功'
        };
      } catch (error) {
        console.error('更新个人简介请求失败:', error);
        return {
          success: false,
          message: error?.message || '更新个人简介请求失败，请稍后再试'
        };
      }
    },
    
    // 修改密码
    async updatePassword(oldPassword, newPassword) {
      try {
        if (!this.token) {
          return {
            success: false,
            message: '未登录'
          };
        }
        
        await userApi.updatePassword({ oldPassword, newPassword });
        
        return {
          success: true,
          message: '密码修改成功'
        };
      } catch (error) {
        console.error('修改密码请求失败:', error);
        return {
          success: false,
          message: error?.message || '修改密码请求失败，请稍后再试'
        };
      }
    }
  },
  
  // 添加持久化配置（v4 格式：key 默认 store id，需显式指定为 user-store 与 getToken() 对齐）
  persist: {
    key: 'user-store',
    storage: localStorage
  }
});
