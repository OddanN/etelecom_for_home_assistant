# Etelecom Integration for Home Assistant

![GitHub Release](https://img.shields.io/github/v/release/OddanN/etelecom_for_home_assistant?style=flat-square)
![GitHub Activity](https://img.shields.io/github/commit-activity/m/OddanN/etelecom_for_home_assistant?style=flat-square)
![License](https://img.shields.io/github/license/OddanN/etelecom_for_home_assistant?style=flat-square)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square)](https://github.com/hacs/integration)

<p align="center">
  <img src="logo.png" alt="Etelecom logo" width="200">
</p>

Интеграция Etelecom (AT-Home) получает данные из личного кабинета [Etelecom](https://my.etelecom.ru/) и создаёт сущности
с основными данными по договору, балансу, тарифу, бонусам и сети.

## Установка

Проще всего установить интеграцию через [Home Assistant Community Store
(HACS)](https://hacs.xyz/). После настройки HACS нажмите кнопку ниже
(требуется настроенный My Home Assistant)
или [добавьте репозиторий вручную как custom repository](https://hacs.xyz/docs/faq/custom_repositories),
после чего интеграция станет доступна для установки как обычная HACS-интеграция.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg?style=flat-square)](https://my.home-assistant.io/redirect/hacs_repository/?owner=OddanN&repository=etelecom_for_home_assistant&category=integration)

## Настройка

После установки настройте интеграцию через интерфейс Home Assistant. YAML-конфигурация не требуется.
Перейдите в `Настройки` → `Устройства и службы`, нажмите `Добавить интеграцию`
или воспользуйтесь кнопкой ниже.

[![Add Integration to your Home Assistant instance.](https://my.home-assistant.io/badges/config_flow_start.svg?style=flat-square)](https://my.home-assistant.io/redirect/config_flow_start/?domain=etelecom_for_home_assistant)

### Подключение

- Введите логин и пароль от личного кабинета Etelecom
- Завершите настройку. Интеграция выполнит авторизацию и создаст сущности аккаунта.

### Параметры интеграции

- `Интервал обновления`: период опроса в часах. По умолчанию `12`, минимум `1`, максимум `24`.

## Entities

На каждую пару логин\пароль интеграция создаёт одно устройство личного кабинета.
Каждое устройство содержит следующие **основные** сущности:

- Общая информация по договору: `Номер счета`, `Контрагент`, `Адрес договора`
- Сетевые данные: `IP Локальный` и `IP Внешний`
- `Баланс денег`: денежный баланс лицевого счёта в `₽`. Атрибуты: общее количество денежных операций `count` и последние
  10
  операций по счету `operation_1 ... operation_10`.
- `Баланс бонусов`: бонусный баланс в `б.`. Атрибуты: общее количество бонусных операций `count` и сами операции с
  бонусным балансом `operation_1 ... operation_N`
- `Следующее списание`: сумма следующего списания в `₽`. Атрибут: дата следующего списания `next_charge_date`.
- `Текущий тариф`: текущая скорость тарифа. Атрибут: `name`.
- `Абонемент`: статус текущего абонемента. Атрибуты включают даты начала и окончания и прочие поля ответа API.

## Blueprints

В репозитории есть готовые blueprint-автоматизации:

### Уведомление о низком балансе

Автоматизация отправляет уведомление, когда сенсор `Баланс денег` опускается ниже заданного порога.

Файл: `blueprints/automation/etelecom/low_money_balance_notification.yaml`

[![Import blueprint into Home Assistant](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://raw.githubusercontent.com/OddanN/etelecom_for_home_assistant/main/blueprints/automation/etelecom/low_money_balance_notification.yaml)

### Нехватка денег перед следующим списанием

Автоматизация отправляет уведомление, когда дата следующего списания уже близко, а текущего баланса денег не хватает на
предстоящее списание.

Файл: `blueprints/automation/etelecom/next_charge_insufficient_balance_notification.yaml`

[![Import blueprint into Home Assistant](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://raw.githubusercontent.com/OddanN/etelecom_for_home_assistant/main/blueprints/automation/etelecom/next_charge_insufficient_balance_notification.yaml)

## Примечания

- Для работы интеграции нужен действующий аккаунт Etelecom.
- Для авторизации используются те же логин и пароль, что и в личном кабинете.
- Если вы нашли ошибку или хотите предложить улучшение, создайте issue в
  [GitHub repository](https://github.com/OddanN/etelecom_for_home_assistant/issues).

## Debug

Для включения DEBUG-логов добавьте в `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.etelecom_for_home_assistant: debug
```

## License

Проект распространяется по лицензии MIT. Подробности в файле [LICENSE](LICENSE).
