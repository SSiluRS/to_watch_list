<template>
  <div>
    <h2>Your Lists</h2>
    <div v-for="list in lists" :key="list.id" class="list">
      <h3>{{ list.name }}</h3>
      <button @click="$emit('openList', list.id, list.name)">Open</button>
      <button @click="renameList(list)">Rename</button>
      <button @click="deleteList(list)">Delete</button>
    </div>
    <button @click="createList">Create New List</button>

    <h2>Shared with You</h2>
    <div v-for="list in shared" :key="list.id" class="shared-list">
      <h3>{{ list.name }} <small>(Shared by {{ list.owner }})</small></h3>
      <button @click="$emit('openList', list.id, list.name)">Open</button>
    </div>

    <button @click="$emit('logout')" style="background:red;margin-top:10px;">Logout</button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const lists = ref([])
const shared = ref([])

async function fetchLists() {
  const res = await api.get('/lists')
  lists.value = res.data
  const resShared = await api.get('/shared_lists')
  shared.value = resShared.data
}

async function createList() {
  const name = prompt('Enter name:')
  if (!name) return
  await api.post('/lists', { name })
  fetchLists()
}

async function renameList(list) {
  const newName = prompt('New name:', list.name)
  if (!newName) return
  await api.patch('/rename_list', { list_id: list.id, new_name: newName })
  fetchLists()
}

async function deleteList(list) {
  if (!confirm('Delete this list?')) return
  await api.delete('/delete_list', { data: { list_id: list.id } })
  fetchLists()
}

onMounted(fetchLists)
</script>
