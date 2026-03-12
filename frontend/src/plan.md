необходимо добавть на страницу Workspace в сайдбар раздел с API ключами, тз: 

1) раздел называется API Keys
2) в самом разделе отображается таблица с ключами, столбцы - Name, Status (должен использоваться компонент StatusBadge, возможные статусы Active, Expired, Inactive), Created at, Expires at - даты в формате ISO, нужно с помощью dayjs переводить в формат 12/11/25, 5:57 PM либо отображается No expiration если нет, и последний столбец с экшенами Edit, Delete (должны быть кнопки в виде иконок, по аналогии с другими таблицами, например Users)
3) в тулбаре должна быть кнопка Create API key
4) раздел должен выглядеть и быть запроган по аналогии с другими похожими разделами (например Users, Logs)
5) по нажатию на Create API key должна появляться модалка , с формой внутри нее, в форме два поля Name(optional) и expires at(optional) (поле со временем)

по запросам - 

1) создание ключа: POST api/tokens/?expires_in=%D0%B5%D1%83%D1%8B%D0%B5

response: {
  "token_id": "string",
  "token": "string",
  "is_active": true,
  "expires_at": "2026-02-11T15:04:13.719Z",
  "created_at": "2026-02-11T15:04:13.719Z"
}

2) GET api/tokens

response: [
  {
    "token_id": "string",
    "token": "string",
    "is_active": true,
    "expires_at": "2026-02-11T15:04:52.757Z",
    "created_at": "2026-02-11T15:04:52.757Z"
  }
]

3) DELETE api/tokens/{token_id}

для всех запросов создать ключи, мутации, апи, модели(типы) и тд, короче по аналогии с другими папками в entities/

entity для токенов пусть будет отдельное и назови его token