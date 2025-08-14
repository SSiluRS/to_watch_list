<template>
  <div>
    <header>
      <h1>To-Watch List</h1>
    </header>

    <div class="container">
      <AuthForm v-if="!isAuth" @login="onLogin" />
      <ListsView v-else-if="view === 'lists'" @logout="logout" @openList="openList" />
      <ItemsView v-else-if="view === 'items'" :listId="currentListId" :listName="currentListName" @back="view='lists'" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import AuthForm from './components/AuthForm.vue'
import ListsView from './components/ListsView.vue'
import ItemsView from './components/ItemsView.vue'

const isAuth = ref(!!localStorage.getItem('token'))
const view = ref('lists')
const currentListId = ref(null)
const currentListName = ref('')

function onLogin() {
  console.log("onLogin")
  isAuth.value = true
  view.value = 'lists'
}

function openList(id, name) {
  currentListId.value = id
  currentListName.value = name
  view.value = 'items'
}

function logout() {
  localStorage.clear()
  isAuth.value = false
  view.value = 'lists'
}
</script>
