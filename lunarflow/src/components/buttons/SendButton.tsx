// SPDX-FileCopyrightText: Copyright © 2024 Lunarbase (https://lunarbase.ai/) <contact@lunarbase.ai>
//
// SPDX-FileContributor: Danilo Gusicuma <danilo@lunarbase.ai>
//
// SPDX-License-Identifier: GPL-3.0-or-later

"use client"

import { SendOutlined } from "@ant-design/icons"
import { Button, Spin } from "antd"
import React, { useState } from "react"

interface SendButtonProps {
  value: string
  onSubmit: () => Promise<void>
}

const SendButton: React.FC<SendButtonProps> = ({ value, onSubmit }) => {
  const [loading, setLoading] = useState<boolean>(false)

  const size = value === '' && !loading ? 0 : 54

  const handleSubmit = async () => {
    setLoading(true)
    await onSubmit()
    setLoading(false)
  }

  return <Button
    type='primary'
    shape='circle'
    onClick={handleSubmit}
    disabled={loading}
    icon={loading ? <Spin /> : <SendOutlined style={{ fontSize: size === 0 ? 0 : `18px` }} />}
    style={{ width: size, height: size, marginLeft: size === 0 ? 0 : 8, minWidth: 0, padding: size === 0 ? 0 : '4px 0', border: size === 0 ? 0 : 1 }}
  />
}

export default SendButton
