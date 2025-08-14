<template>
  <div id="items-section">
    <div class="list-header">
      <button class="back-button" @click="$emit('back')">
        <img src="/images/left.png" alt="Back" class="back-icon" />
      </button>

      <h2>{{ listName }}</h2>

      <!-- Контролы сортировки и фильтра -->
        <div class="sort-controls">
        <label>
            Сортировать по:
            <select v-model="sort.field" @change="onSortChange">
            <option value="created_at">добавлению</option>
            <option value="title">названию</option>
            <option value="year">году</option>
            <option value="rating">рейтингу</option>
            <option value="genre">жанру</option>
            </select>
        </label>

        <label>
            Порядок:
            <select v-model="sort.order" @change="onSortChange">
            <option value="asc">по возрастанию</option>
            <option value="desc">по убыванию</option>
            </select>
        </label>

        <label>
            Жанр:
            <select v-model="genreFilter" @change="fetchItems">
            <option value="">Все</option>
            <option v-for="g in genres" :key="g" :value="g">{{ g }}</option>
            </select>
        </label>
        </div>

        <button id="share-list-button" @click="shareList">Share List</button>
    </div>

    <KinopoiskSearch :listId="listId" @added="fetchItems" />

    <div id="items-container">
      <div v-for="item in items" :key="item.id" class="item" :class="{ watched: item.watched }">
        <img :src="item.cover_url || 'placeholder.jpg'" :alt="item.title" />
        <div class="item-content">
          <strong>{{ item.title }} ({{ item.type }})</strong>
          <div v-if="item.year">Год: {{ item.year }}</div>
          <div v-if="item.genre">Жанр: {{ item.genre }}</div>

          <div class="full-description" v-if="expandedItemId === item.id">
            {{ item.description }}
          </div>

          <div class="item-buttons">
            <button @click="toggleDescription(item)">
              {{ expandedItemId === item.id ? 'Скрыть' : 'Подробнее' }}
            </button>
            <button @click="toggleWatched(item)">
              {{ item.watched ? 'Unwatch' : 'Watched' }}
            </button>
            <button @click="deleteItem(item)">Delete</button>
          </div>
        </div>
      </div>

      <div v-if="items.length === 0 && !loading" class="status" style="padding:8px;">Нет элементов</div>
      <div v-if="loading" class="status" style="padding:8px;">Загрузка…</div>
      <div v-if="error" class="status" style="color:#b00020; padding:8px;">{{ error }}</div>
    </div>

    <!-- Пейджер (опционально; можно убрать если не нужен) -->
    <div class="item-buttons" style="justify-content:center; margin-top:10px;">
      <button @click="prevPage" :disabled="offset === 0 || loading">Назад</button>
      <span style="align-self:center; padding: 0 8px;">стр. {{ page + 1 }}</span>
      <button @click="nextPage" :disabled="!hasMore || loading">Вперёд</button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import api from '../api'
import KinopoiskSearch from './KinopoiskSearch.vue'

const props = defineProps({
  listId: Number,
  listName: String
})

const items = ref([])
const expandedItemId = ref(null)
const loading = ref(false)
const error = ref('')

// серверная сортировка + пагинация
const sort = reactive({
  field: localStorage.getItem('sort.field') || 'created_at',
  order: localStorage.getItem('sort.order') || 'desc'
})
const genreFilter = ref('')
const genres = ref([]) 
const limit = ref(10)
const offset = ref(0)
const hasMore = ref(false)
const page = computed(() => Math.floor(offset.value / limit.value))

async function fetchGenres() {
  try {
    const res = await api.get('/items/genres', { params: { list_id: props.listId } })
    genres.value = res.data || []
  } catch (e) {
    console.error('Ошибка загрузки жанров', e)
  }
}

async function fetchItems() {
  loading.value = true
  error.value = ''
  try {
    console.log(genreFilter)
    const res = await api.get('/items', {
      params: {
        list_id: props.listId,
        sort_by: sort.field,   // требует серверной поддержки (см. правку main.py ниже)
        order: sort.order,
        limit: limit.value,
        offset: offset.value,
        genre_filter: genreFilter.value || undefined
      }
    })
    // поддержим обе формы ответа: старую (массив) и новую ({items: [...]})
    items.value = Array.isArray(res.data?.items) ? res.data.items : (Array.isArray(res.data) ? res.data : [])
    hasMore.value = items.value.length === Number(limit.value)
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.message || 'Ошибка загрузки'
  } finally {
    loading.value = false
  }
}

function onSortChange() {
  localStorage.setItem('sort.field', sort.field)
  localStorage.setItem('sort.order', sort.order)
  offset.value = 0
  fetchItems()
}

function nextPage() {
  if (hasMore.value) {
    offset.value += Number(limit.value)
    fetchItems()
  }
}
function prevPage() {
  offset.value = Math.max(0, offset.value - Number(limit.value))
  fetchItems()
}

async function toggleWatched(item) {
  await api.patch('/items', { id: item.id, watched: !item.watched })
  fetchItems()
}

async function deleteItem(item) {
  if (!confirm('Delete this item?')) return
  await api.delete('/items', { data: { id: item.id } })
  fetchItems()
}

async function shareList() {
  const username = prompt('Enter username to share with:')
  if (!username) return
  await api.post('/share', { list_id: props.listId, username })
  alert(`List shared with ${username}!`)
}

async function toggleDescription(item) {
  if (expandedItemId.value === item.id) {
    expandedItemId.value = null
    return
  }
  expandedItemId.value = item.id

  if (!item.title || !item.title.trim()) return
  try {
    const res = await api.get('/kinopoisk/description', {
      params: {
        query: item.title || item.name,
        type: item.type || undefined,   // 'movie' | 'tv-series' | ...
        year: item.year || undefined
      }
    })
    item.description = res.data?.description || 'Нет описания'
  } catch (err) {
    console.error('Kinopoisk API error', err)
  }
}

onMounted(() => {
  fetchGenres()
  fetchItems()
})
</script>
