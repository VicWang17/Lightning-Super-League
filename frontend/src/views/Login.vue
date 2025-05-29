<template>
  <div class="login-container">
    <div class="login-card">
      <div class="logo-section">
        <h1 class="logo">⚡闪电超级联赛</h1>
        <p class="tagline">开启你的足球经理之旅</p>
      </div>

      <n-tabs v-model:value="activeTab" type="line" animated>
        <n-tab-pane name="login" tab="登录">
          <n-form ref="loginFormRef" :model="loginForm" :rules="loginRules">
            <n-form-item path="username" label="用户名">
              <n-input v-model:value="loginForm.username" placeholder="请输入用户名" />
            </n-form-item>
            <n-form-item path="password" label="密码">
              <n-input 
                v-model:value="loginForm.password" 
                type="password" 
                placeholder="请输入密码"
                @keyup.enter="handleLogin"
              />
            </n-form-item>
            <n-form-item>
              <n-button 
                type="primary" 
                size="large" 
                block 
                :loading="loginLoading"
                @click="handleLogin"
              >
                登录
              </n-button>
            </n-form-item>
          </n-form>
        </n-tab-pane>

        <n-tab-pane name="register" tab="注册">
          <n-form ref="registerFormRef" :model="registerForm" :rules="registerRules">
            <n-form-item path="username" label="用户名">
              <n-input v-model:value="registerForm.username" placeholder="请输入用户名" />
            </n-form-item>
            <n-form-item path="email" label="邮箱">
              <n-input v-model:value="registerForm.email" placeholder="请输入邮箱" />
            </n-form-item>
            <n-form-item path="password" label="密码">
              <n-input v-model:value="registerForm.password" type="password" placeholder="请输入密码" />
            </n-form-item>
            <n-form-item path="confirmPassword" label="确认密码">
              <n-input 
                v-model:value="registerForm.confirmPassword" 
                type="password" 
                placeholder="请再次输入密码"
                @keyup.enter="handleRegister"
              />
            </n-form-item>
            <n-form-item>
              <n-button 
                type="primary" 
                size="large" 
                block 
                :loading="registerLoading"
                @click="handleRegister"
              >
                注册
              </n-button>
            </n-form-item>
          </n-form>
        </n-tab-pane>
      </n-tabs>

      <div class="back-home">
        <n-button text @click="$router.push('/')">
          ← 返回首页
        </n-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { NTabs, NTabPane, NForm, NFormItem, NInput, NButton, useMessage } from 'naive-ui'

const router = useRouter()
const message = useMessage()

const activeTab = ref('login')
const loginLoading = ref(false)
const registerLoading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在 3 到 20 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于 6 个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (rule: any, value: string) => {
        return value === registerForm.password
      },
      message: '两次输入的密码不一致',
      trigger: 'blur'
    }
  ]
}

const handleLogin = async () => {
  try {
    loginLoading.value = true
    
    // 模拟登录API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // 临时存储token（后续需要对接真实API）
    localStorage.setItem('token', 'demo-token')
    localStorage.setItem('username', loginForm.username)
    
    message.success('登录成功！')
    router.push('/dashboard')
  } catch (error) {
    message.error('登录失败，请检查用户名和密码')
  } finally {
    loginLoading.value = false
  }
}

const handleRegister = async () => {
  try {
    registerLoading.value = true
    
    // 模拟注册API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    message.success('注册成功！请登录')
    activeTab.value = 'login'
    
    // 清空注册表单
    Object.assign(registerForm, {
      username: '',
      email: '',
      password: '',
      confirmPassword: ''
    })
  } catch (error) {
    message.error('注册失败，请稍后重试')
  } finally {
    registerLoading.value = false
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, 
    rgba(0, 176, 81, 0.1) 0%, 
    rgba(255, 102, 0, 0.1) 50%, 
    rgba(0, 0, 0, 0.9) 100%
  );
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 400px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(10px);
}

.logo-section {
  text-align: center;
  margin-bottom: 30px;
}

.logo {
  font-size: 2rem;
  font-weight: 900;
  background: linear-gradient(135deg, #00b051, #ffd700);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 8px;
}

.tagline {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.back-home {
  text-align: center;
  margin-top: 20px;
}

:deep(.n-tabs .n-tabs-nav) {
  background: transparent;
}

:deep(.n-tabs .n-tab-pane) {
  padding-top: 20px;
}

:deep(.n-form-item-label) {
  color: var(--text-primary);
}
</style> 