// Copyright © 2024 Idiap Research Institute <contact@idiap.ch>
// SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
//
// SPDX-License-Identifier: GPL-3.0-or-later

import api from "@/app/api/lunarverse"
import { useUserId } from "@/hooks/useUserId"
import { File } from "@/models/File"
import { UploadOutlined } from "@ant-design/icons"
import { Button, Select, Upload } from "antd"
import { RcFile } from "antd/es/upload"
import { AxiosResponse } from "axios"
import { useParams } from "next/navigation"
import { UploadRequestOption } from "rc-upload/lib/interface"
import React, { useEffect, useState } from "react"

interface Option {
  value: string
  label: string
}

interface FileInputProps {
  value?: string
  onInputChange: (value: File) => void
}

const FileInput: React.FC<FileInputProps> = ({ value, onInputChange }) => {

  const [options, setOptions] = useState<Option[]>([])
  const [loading, setLoading] = useState<boolean>(false)
  const [selectValue, setSelectValue] = useState<string>('upload')
  const userId = useUserId()

  const { id: workflowId } = useParams()

  useEffect(() => {
    fetchFiles()
  }, [])

  const addOption = (file: File): Option[] => {
    if (file.path != null) {
      return [{ value: file.path, label: file.path?.split('/').pop() ?? 'Undefined' }, ...options]
    } else {
      return options
    }
  }

  const generateOptions = (files: string[]): Option[] => {
    const options: Option[] = files.map(file => ({ value: file, label: file.split('/').pop() ?? 'Undefined' }))
    return [{ value: "upload", label: "New Upload" }, ...options]
  }

  const onUpload = async ({ file, filename, data: uploadData, onSuccess, onError, onProgress }: UploadRequestOption) => {
    const formData = new FormData();
    if (uploadData) {
      Object.keys(uploadData).forEach(key => {
        formData.append(key, uploadData[key] as Blob);
      });
    }
    formData.append(filename ?? '', file);
    const { data: response } = await api.post<any, AxiosResponse<string, any>>(`/file/${workflowId}/upload?user_id=${userId}`, formData, {
      onUploadProgress: ({ total, loaded }) => {
        if (onProgress != null) onProgress({ percent: Math.round((loaded / (total ?? 1)) * 100) });
      }
    })
    if (onSuccess) onSuccess(response)
    const uploadedFile = file as RcFile
    const filepath: string = `${response}/${uploadedFile.name}`
    const fileObject: File = {
      path: filepath,
      name: filename,
    }
    setOptions(addOption(fileObject))
    setSelectValue(filepath)
    onInputChange(fileObject)
  }

  const fetchFiles = async () => {
    const { data: response } = await api.get<string[]>(`/file/${workflowId}?user_id=${userId}`)
    setOptions(generateOptions(response))
  }

  const onSelectChange = (value: string) => {
    setSelectValue(value)
    const fileObject = {
      path: value,
      name: value.split('/').pop() ?? 'Undefined',
    }
    onInputChange(fileObject)
  }

  return <>
    <Select
      value={selectValue}
      options={options}
      onChange={onSelectChange}
      onSelect={fetchFiles}
      loading={loading}
      className="nodrag nowheel"
    />
    {selectValue === "upload" ? <Upload
      customRequest={onUpload}
      multiple={true}
    >
      <Button
        style={{ width: '100%', marginTop: '16px' }}
        icon={<UploadOutlined />}
      >
        Click to Upload
      </Button>
    </Upload> : <></>}
  </>
}

export default FileInput
